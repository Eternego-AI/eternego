"""Conscious — the waking thinking pipeline.

Five functions run in sequence by the clock tick:
  understand → recognize → wonder → decide → conclude
"""

from application.core.data import Prompt
from application.core.brain import perceptions, signals
from application.core import channels
from application.platform import logger


# ── Understanding ────────────────────────────────────────────────────────────

async def understand(reason, mind) -> None:
    """Route unattended signals to existing or new perception threads."""
    logger.info("Understanding", {"persona": mind.persona})
    if not mind.unattended:
        return

    logger.debug("Understand", {"persona": mind.persona, "unattended": mind.unattended})

    known = mind.perceptions
    thread_map = {i + 1: p for i, p in enumerate(known)}
    unattended = list(mind.unattended)
    signal_map = {i + 1: s for i, s in enumerate(unattended)}

    system = (
        "# Task: Route incoming signals to conversation threads\n"
        "Threads and signals are both numbered. For each signal number, return the thread "
        "number(s) it continues, or a concise impression if it starts a new topic. "
        "A signal can belong to multiple threads if it spans subjects.\n\n"
        "Return routes ordered by importance — most urgent or significant thread first.\n\n"
        "Return JSON:\n"
        "{\n"
        '  "routes": [\n'
        '    {"signal": 1, "threads": [1, 3], "new_impressions": ["new topic"]}\n'
        "  ]\n"
        "}\n"
        "Use empty lists when not applicable. Prefer threads over new_impressions."
    )

    prompts = [Prompt(role="user", content=(
        "Known threads:\n"
        f"{"\n\n".join(f"{i}.\n{perceptions.thread(p)}" for i, p in thread_map.items()) if known else "None"}\n\n"
        "Signals to route:\n"
        f"{"\n".join(f"{i}. {signals.labeled(s)}" for i, s in signal_map.items())}\n\n"
        "Route each signal by its number."
    ))]

    result = await reason(mind.persona, system, prompts)
    routes = result.get("routes", [])

    routed = set()
    for route in routes:
        signal_num = route.get("signal")
        if not isinstance(signal_num, (int, float)):
            continue
        signal = signal_map.get(int(signal_num))
        if not signal:
            continue

        routed.add(signal.id)

        for thread_num in route.get("threads", []):
            perception = thread_map.get(thread_num)
            if perception:
                mind.understand(signal, perception.impression)

        for impression in route.get("new_impressions", []):
            if impression:
                mind.understand(signal, impression)

        if not route.get("threads") and not route.get("new_impressions"):
            mind.understand(signal, signal.content[:60])

    # Fallback: signals the LLM failed to route get their own perception
    for signal in unattended:
        if signal.id not in routed:
            logger.warning("understand: unrouted signal, using fallback", {"signal_id": signal.id})
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

    system = (
        thought.meaning.path()
        + "\n\nAlways include a \"recap\" field — a brief one-sentence summary of what "
        "you are doing or have done.\n"
        "If the task is already fulfilled based on the conversation, do not take "
        "further action. Return only: {\"recap\": \"what was accomplished\"}"
    )
    prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

    result = await reason(mind.persona, system, prompts)
    recap = result.pop("recap", None) if isinstance(result, dict) else None

    if not result:
        if recap:
            mind.answer(thought, recap)
        mind.resolve(thought)
        return

    decision_text = json.dumps(result)
    mind.answer(thought, decision_text)

    signal = await thought.meaning.run(result)

    if signal is None:
        if recap:
            mind.answer(thought, recap)
        mind.resolve(thought)
    else:
        mind.inform(thought, signal)


# ── Concluding ───────────────────────────────────────────────────────────────

async def conclude(reply, mind) -> None:
    """Summarize for the person and mark the thought as concluded.

    No archiving — thread stays in memory until sleep.
    """
    logger.info("Concluding", {"persona": mind.persona})
    from application.platform import datetimes

    thought = mind.most_important_thought(mind.concluded)
    if not thought:
        return

    logger.debug("conclude", {"persona": mind.persona, "impression": thought.perception.impression})

    summary_prompt = thought.meaning.summarize()
    if summary_prompt:
        channel = channels.latest(mind.persona) or channels.default_channel(mind.persona)

        system = "# This Interaction\n" + "\n".join(filter(None, [
            thought.meaning.description(),
            summary_prompt,
        ]))
        prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

        text = ""
        async for paragraph in reply(mind.persona, system, prompts):
            await channels.send(channel, paragraph)
            text += ("\n" if text else "") + paragraph

        if text:
            mind.answer(thought, text)

    thought.concluded_at = datetimes.now()
