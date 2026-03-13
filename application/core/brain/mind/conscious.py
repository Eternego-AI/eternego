"""Conscious — the waking thinking pipeline.

Five functions run in sequence by the clock tick:
  understand → recognize → wonder → decide → conclude
"""

from application.core.data import Prompt
from application.core.brain import perceptions, signals
from application.core import channels, paths
from application.platform import logger


# ── Understanding ────────────────────────────────────────────────────────────

async def understand(reason, mind) -> None:
    """Route unattended signals to existing or new perception threads."""
    logger.info("Understanding", {"persona": mind.persona})
    if not mind.unattended:
        return

    logger.debug("Understand", {"persona": mind.persona, "unattended": mind.unattended})

    known = mind.perceptions
    row_map = {i + 1: p for i, p in enumerate(known)}

    system = (
        "# Task: Route incoming signals to conversation threads\n"
        "Each known thread is numbered. For each signal, return the row number(s) "
        "of threads it continues, or a concise impression if it starts "
        "a new topic. A signal can belong to multiple threads if it spans subjects.\n\n"
        "Return routes ordered by importance — most urgent or significant thread first.\n\n"
        "Return JSON:\n"
        "{\n"
        '  "routes": [\n'
        '    {"signal_id": "...", "rows": [1, 3], "new_impressions": ["new topic"]}\n'
        "  ]\n"
        "}\n"
        "Use empty lists when not applicable. Prefer rows over new_impressions."
    )

    prompts = [Prompt(role="user", content=(
        "Known threads:\n"
        f"{"\n\n".join(f"{i}.\n{perceptions.thread(p)}" for i, p in row_map.items()) if known else "None"}\n\n"
        "Signals to route:\n"
        f"{"\n".join(f"- {signals.labeled(s)}" for s in mind.unattended)}\n\n"
        "Route each signal using row numbers or new impressions."
    ))]

    result = await reason(mind.persona, system, prompts)
    routes = result.get("routes", [])

    signal_map = {s.id: s for s in mind.unattended}

    for route in routes:
        signal = signal_map.get(route.get("signal_id"))
        if not signal:
            continue

        for row in route.get("rows", []):
            perception = row_map.get(row)
            if perception:
                mind.understand(signal, perception.impression)

        for impression in route.get("new_impressions", []):
            if impression:
                mind.understand(signal, impression)

        if not route.get("rows") and not route.get("new_impressions"):
            mind.understand(signal, signal.content[:60])


# ── Recognition ──────────────────────────────────────────────────────────────

async def recognize(reason, mind) -> None:
    """Match the most important unrecognized perception to a meaning."""
    logger.info("Recognizing", {"persona": mind.persona})
    perception = mind.most_important_perception
    if not perception:
        return

    logger.debug("Recognize", {"persona": mind.persona, "impression": perception.impression})

    system = (
        "# Task: Match a conversation thread to a meaning\n"
        "Given a numbered list of known meanings and a conversation thread, "
        "return the row number of the best-matching meaning.\n"
        "Use the Escalation row if no meaning fits.\n\n"
        "Return JSON:\n"
        '{"meaning_row": N}'
    )

    prompts = [Prompt(role="user", content=(
        "Known meanings:\n"
        f"{"\n".join(f"{i + 1}. {m.name}: {m.description()}" for i, m in enumerate(mind.meanings))}\n\n"
        "Thread to match:\n"
        f"{perceptions.thread(perception)}\n\n"
        "Return the row number of the best-matching meaning."
    ))]

    result = await reason(mind.persona, system, prompts)
    row = result.get("meaning_row")

    escalation = next(m for m in mind.meanings if m.name == "Escalation")
    if isinstance(row, (int, float)) and 1 <= int(row) <= len(mind.meanings):
        meaning = mind.meanings[int(row) - 1]
    else:
        meaning = escalation

    # Escalation → try generating a new meaning via frontier/local model
    if meaning.name == "Escalation":
        from application.core.brain import ego
        from application.core.brain.mind import meanings as meanings_module
        code = await ego.escalate(mind.persona, perceptions.thread(perception), mind.meanings)
        if code:
            try:
                new_meaning = meanings_module.learn(mind.persona, code)
                mind.add_meanings(new_meaning)
                meaning = new_meaning
            except Exception as e:
                logger.error("recognize: failed to learn meaning", {"persona": mind.persona, "error": str(e)})

    mind.recognize(perception, meaning)


# ── Wondering ────────────────────────────────────────────────────────────────

async def wonder(reply, mind) -> None:
    """Generate a streaming reply for the most important unanswered thought."""
    logger.info("Wondering", {"persona": mind.persona})
    thought = mind.most_important_thought(mind.unanswered)
    if not thought:
        return

    m = thought.meaning
    has_replied = any(s.role == "assistant" for s in thought.perception.thread)
    prompt = m.clarify() if has_replied else m.reply()
    if prompt is None:
        return

    logger.debug("Wonder", {"persona": mind.persona, "impression": thought.perception.impression})

    channel = channels.latest(mind.persona) or channels.default_channel(mind.persona)

    system = "# This Interaction\n" + "\n".join(filter(None, [
        m.description(),
        prompt,
    ]))

    prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

    text = ""
    async for paragraph in reply(mind.persona, system, prompts):
        if mind.unattended:
            break
        if channel:
            await channels.send(channel, paragraph)
        text += ("\n" if text else "") + paragraph

    if text:
        mind.answer(thought, text)

    if not thought.meaning.path():
        mind.resolve(thought)


# ── Deciding ─────────────────────────────────────────────────────────────────

async def decide(reason, mind) -> None:
    """Execute the action for the most important pending thought."""
    logger.info("Deciding", {"persona": mind.persona})
    import json

    thought = mind.most_important_thought(mind.pending)
    if not thought:
        return

    logger.debug("Decide", {"persona": mind.persona, "impression": thought.perception.impression})

    system = thought.meaning.path()
    prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

    result = await reason(mind.persona, system, prompts)

    # Add model's decision as assistant signal to the thread
    decision_text = json.dumps(result) if isinstance(result, dict) else str(result)
    mind.answer(thought, decision_text)

    signal = await thought.meaning.run(result)

    if signal is None:
        mind.resolve(thought)
    else:
        mind.inform(thought, signal)


# ── Concluding ───────────────────────────────────────────────────────────────

async def conclude(reply, mind) -> None:
    """Archive the conversation, recap it, and forget the thought."""
    logger.info("Concluding", {"persona": mind.persona})
    thought = mind.most_important_thought(mind.concluded)
    if not thought:
        return

    logger.debug("conclude", {"persona": mind.persona, "impression": thought.perception.impression})

    # Archive first — get the filename
    thread_text = perceptions.thread(thought.perception)
    filename = paths.add_history_entry(mind.persona.id, thought.perception.impression, thread_text)
    recap = None

    if thought.meaning.path():
        channel = channels.latest(mind.persona) or channels.default_channel(mind.persona)
        system = (
            "Generate a brief, natural recap of what was accomplished in this conversation. "
            "Be concise — one or two sentences."
        )
        prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

        recap = ""
        async for paragraph in reply(mind.persona, system, prompts):
            if mind.unattended:
                return  # incomplete recap — retry next cycle
            recap += ("\n" if recap else "") + paragraph

        if recap:
            if channel:
                await channels.send(channel, recap)

    # Remember recap with filepath so subconscious can find the full conversation
    if recap is not None:
        mind.remember(f"{filename}\n{recap}")

    mind.forget(thought)
