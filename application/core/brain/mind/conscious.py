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
    if not mind.unattended:
        return

    persona = mind.persona
    logger.info("understand", {"unattended": len(mind.unattended)})

    known = mind.perceptions
    row_map = {i + 1: p for i, p in enumerate(known)}

    threads_text = "\n\n".join(
        f"{i}.\n{perceptions.thread(p)}" for i, p in row_map.items()
    ) if known else "None"

    signals_text = "\n".join(
        f"- {signals.labeled(s)}" for s in mind.unattended
    )

    system = (
        "# Task: Route incoming signals to conversation threads\n"
        "Each known thread is numbered. For each signal, return the row number(s) "
        "of threads it continues, or a new short impression (max 8 words) if it starts "
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
        f"Known threads:\n{threads_text}\n\n"
        f"Signals to route:\n{signals_text}\n\n"
        "Route each signal using row numbers or new impressions."
    ))]

    result = await reason(persona, system, prompts)
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
    perception = mind.most_important_perception
    if not perception:
        return

    persona = mind.persona
    logger.info("recognize", {"impression": perception.impression})

    meanings = mind.meanings
    meanings_text = "\n".join(
        f"{i + 1}. {m.name}: {m.description()}" for i, m in enumerate(meanings)
    )

    system = (
        "# Task: Match a conversation thread to a meaning\n"
        "Given a numbered list of known meanings and a conversation thread, "
        "return the row number of the best-matching meaning.\n"
        "Use the Escalation row if no meaning fits.\n\n"
        "Return JSON:\n"
        '{"meaning_row": N}'
    )

    prompts = [Prompt(role="user", content=(
        f"Known meanings:\n{meanings_text}\n\n"
        f"Thread to match:\n{perceptions.thread(perception)}\n\n"
        "Return the row number of the best-matching meaning."
    ))]

    result = await reason(persona, system, prompts)
    row = result.get("meaning_row")

    escalation = next((m for m in meanings if m.name == "Escalation"), meanings[-1])
    if isinstance(row, (int, float)) and 1 <= int(row) <= len(meanings):
        meaning = meanings[int(row) - 1]
    else:
        meaning = escalation

    mind.recognize(perception, meaning)


# ── Wondering ────────────────────────────────────────────────────────────────

async def wonder(reply, mind) -> None:
    """Generate a streaming reply for the most important unanswered thought."""
    thought = mind.most_important_thought(mind.unanswered)
    if not thought:
        return

    persona = mind.persona
    logger.info("wonder", {"impression": thought.perception.impression})

    channel = channels.latest(persona) or channels.default_channel(persona)

    m = thought.meaning
    system = "# This Interaction\n" + "\n".join(filter(None, [
        m.description(),
        m.clarification(),
        m.reply(),
    ]))

    prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

    text = ""
    async for paragraph in reply(persona, system, prompts):
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
    thought = mind.most_important_thought(mind.pending)
    if not thought:
        return

    persona = mind.persona
    logger.info("decide", {"impression": thought.perception.impression, "priority": thought.priority})

    system = thought.meaning.path()
    prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

    result = await reason(persona, system, prompts)

    signal = await thought.meaning.run(result)

    if signal is None:
        mind.resolve(thought)
    else:
        mind.inform(thought, signal)


# ── Concluding ───────────────────────────────────────────────────────────────

async def conclude(reply, mind) -> None:
    """Archive the conversation, recap it, and forget the thought."""
    thought = mind.most_important_thought(mind.concluded)
    if not thought:
        return

    persona = mind.persona
    logger.info("conclude", {"impression": thought.perception.impression})

    # Archive first — get the filename
    thread_text = perceptions.thread(thought.perception)
    filename = paths.add_history_entry(persona.id, thought.perception.impression, thread_text)
    recap = None

    if thought.meaning.path():
        channel = channels.latest(persona) or channels.default_channel(persona)
        system = (
            "Generate a brief, natural recap of what was accomplished in this conversation. "
            "Be concise — one or two sentences."
        )
        prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

        recap = ""
        async for paragraph in reply(persona, system, prompts):
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
