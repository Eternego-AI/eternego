"""Conscious — the waking thinking pipeline.

Five functions run in sequence by the clock tick:
  realize → understand → recognize → decide → conclude
"""

import uuid

from application.core.brain.data import Signal, SignalEvent
from application.core.brain import perceptions, signals
from application.core import channels, agents, local_model
from application.platform import logger


# ── Realizing ─────────────────────────────────────────────────────────────────

async def realize(mind) -> None:
    """Route unattended signals to existing or new perception threads."""
    if not mind.needs_realizing:
        logger.debug("Nothing to realize", {"persona": mind.persona})
        return

    logger.debug("Realize", {"persona": mind.persona, "unattended": mind.needs_realizing})

    await channels.express_thinking(mind.persona)

    known = mind.perceptions
    thread_map = {i + 1: p for i, p in enumerate(known)}
    unattended = list(mind.needs_realizing)
    signal_map = {i + 1: s for i, s in enumerate(unattended)}

    threads_text = "\n\n".join(
        f"{i}. {p.impression}\n{perceptions.conversation(p)}"
        for i, p in thread_map.items()
    ) if known else "None"

    signals_text = "\n".join(
        f"{i}. {signals.labeled(s)}"
        for i, s in signal_map.items()
    )

    ego = agents.persona(mind.persona)
    system = (
        ego.identity()
        + "\n\n# Task: Route incoming signals to conversation threads\n"
        "Threads and signals are both numbered. For each signal number, decide:\n"
        "- Does it **directly continue** an existing thread? Only if it is a reply or follow-up "
        "to that specific conversation topic. A new unrelated message does NOT continue a thread "
        "just because the same person sent it.\n"
        "- Otherwise, create a new impression that captures the topic.\n\n"
        "Return routes ordered by importance — most urgent or significant first.\n\n"
        "Return JSON:\n"
        "{\n"
        '  "routes": [\n'
        '    {"signal": 1, "threads": [1], "new_impressions": ["new topic"]}\n'
        "  ]\n"
        "}\n"
        "Use empty lists when not applicable. When in doubt, prefer a new impression "
        "over forcing a signal into an unrelated thread.\n\n"
        f"Known threads:\n{threads_text}\n\n"
        f"Signals to route:\n{signals_text}"
    )

    messages = [{"role": "system", "content": system}, {"role": "user", "content": "Route each signal by its number."}]
    result = await local_model.chat_json_stream(mind.persona.model.name, messages)
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
                mind.realize(signal, perception.impression)

        for impression in route.get("new_impressions", []):
            if impression:
                mind.realize(signal, impression)

        if not route.get("threads") and not route.get("new_impressions"):
            logger.warning("realize: route with no threads or impressions", {"signal_id": signal.id})

    for signal in unattended:
        if signal.id not in routed:
            logger.warning("realize: unrouted signal, stays unattended", {"signal_id": signal.id})


# ── Understanding ────────────────────────────────────────────────────────────

async def understand(mind) -> None:
    """Match the most important unrecognized perception to a meaning."""
    perception = mind.most_important_perception
    if not perception:
        logger.debug("Nothing to understand", {"persona": mind.persona})
        return

    logger.debug("Understand", {"persona": mind.persona, "impression": perception.impression})

    await channels.express_thinking(mind.persona)

    meanings_text = "\n".join(
        f"{i + 1}. {m.name}: {m.description()}"
        for i, m in enumerate(mind.meanings)
    )

    ego = agents.persona(mind.persona)
    system = (
        ego.identity()
        + "\n\n# Task: Match a conversation thread to a meaning\n"
        "Given a numbered list of known meanings and a conversation thread, "
        "return the row number of the best-matching meaning.\n"
        "Use the Escalation row if no meaning fits.\n\n"
        "Return JSON:\n"
        '{"meaning_row": N}\n\n'
        f"Known meanings:\n{meanings_text}\n\n"
        "Return the row number of the best-matching meaning."
    )

    messages = [{"role": "system", "content": system}] + perceptions.to_conversation(perception.thread)
    result = await local_model.chat_json_stream(mind.persona.model.name, messages)
    row = result.get("meaning_row")

    escalation = next(m for m in mind.meanings if m.name == "Escalation")
    if isinstance(row, (int, float)) and 1 <= int(row) <= len(mind.meanings):
        meaning = mind.meanings[int(row) - 1]
    else:
        meaning = escalation

    # Escalation → try generating a new meaning via frontier/local model
    if meaning.name == "Escalation":
        from application.core.brain.mind import meanings as meanings_module
        code = await ego.escalate(perceptions.thread(perception), mind.meanings)
        if code:
            try:
                new_meaning = meanings_module.learn(mind.persona, code)
                mind.add_meanings(new_meaning)
                meaning = new_meaning
            except Exception as e:
                logger.error("understand: failed to learn meaning", {"persona": mind.persona, "error": str(e)})

    mind.understand(perception, meaning)


# ── Recognition ──────────────────────────────────────────────────────────────

async def recognize(mind) -> None:
    """Generate a reply for the most important thought that needs recognition."""
    thought = mind.most_important_thought(mind.needs_recognition)
    if not thought:
        logger.debug("Nothing to recognize", {"persona": mind.persona})
        return

    await channels.express_thinking(mind.persona)

    m = thought.meaning
    last = thought.perception.thread[-1].event if thought.perception.thread else ""
    if last == SignalEvent.executed:
        prompt = m.clarify()
        event = SignalEvent.clarified
    else:
        prompt = m.reply()
        event = SignalEvent.answered

    if prompt is None:
        return

    logger.debug("Recognize", {"persona": mind.persona, "impression": thought.perception.impression, "event": event})

    ego = agents.persona(mind.persona)
    await channels.express_thinking(mind.persona)

    system = ego.identity() + "\n\n# This Interaction\n" + "\n".join(filter(None, [
        m.description(),
        prompt,
    ]))

    messages = [{"role": "system", "content": system}] + mind.prompts(thought)
    text = await local_model.chat(mind.persona.model.name, messages)

    if text:
        await ego.say(text)
        mind.answer(thought, text, event)

    if not m.path():
        mind.forget(thought)


# ── Deciding ─────────────────────────────────────────────────────────────────

async def decide(mind) -> None:
    """Execute the action for the most important pending thought."""
    import json

    thought = mind.most_important_thought(mind.needs_decision)
    if not thought:
        logger.debug("Nothing to decide", {"persona": mind.persona})
        return

    await channels.express_thinking(mind.persona)

    logger.debug("Decide", {"persona": mind.persona, "impression": thought.perception.impression})

    ego = agents.persona(mind.persona)
    system = (
        ego.identity()
        + "\n\n" + thought.meaning.path()
        + "\n\nAdd a \"recap\" field to your JSON — one sentence on what you did or are doing.\n"
        "If already fulfilled, return just: {\"recap\": \"what was accomplished\"}."
    )
    messages = [{"role": "system", "content": system}] + mind.prompts(thought)
    result = await local_model.chat_json_stream(mind.persona.model.name, messages)
    recap = result.pop("recap", None) if isinstance(result, dict) else None

    if not result:
        mind.answer(thought, recap or "", SignalEvent.recap)
        return

    decision_text = json.dumps(result)
    mind.answer(thought, decision_text, SignalEvent.decided)

    try:
        action = await thought.meaning.run(result)
    except Exception as e:
        logger.error("Decide: run failed", {"persona": mind.persona, "error": str(e)})
        mind.inform(thought, Signal(
            id=str(uuid.uuid4()), event=SignalEvent.executed,
            content=f"[{thought.meaning.name}: {decision_text}] Error: {e}",
        ))
        return

    if action is None:
        mind.answer(thought, recap or "", SignalEvent.recap)
        return

    try:
        output = await action()
    except Exception as e:
        logger.error("Decide: action failed", {"persona": mind.persona, "error": str(e)})
        output = f"Error: {e}"

    if output is not None:
        content = f"[{thought.meaning.name}: {decision_text}]"
        if output:
            content += f" {output}"
        mind.inform(thought, Signal(
            id=str(uuid.uuid4()), event=SignalEvent.executed,
            content=content,
        ))
    else:
        mind.answer(thought, recap or "", SignalEvent.recap)


# ── Concluding ───────────────────────────────────────────────────────────────

async def conclude(mind) -> None:
    """Summarize for the person and mark the thought as concluded."""
    thought = mind.most_important_thought(mind.needs_conclusion)
    if not thought:
        logger.debug("Nothing to conclude", {"persona": mind.persona})
        return

    await channels.express_thinking(mind.persona)

    logger.debug("Conclude", {"persona": mind.persona, "impression": thought.perception.impression})

    summary_prompt = thought.meaning.summarize()
    if summary_prompt:
        ego = agents.persona(mind.persona)
        await channels.express_thinking(mind.persona)

        system = ego.identity() + "\n\n# This Interaction\n" + "\n".join(filter(None, [
            thought.meaning.description(),
            summary_prompt,
        ]))
        messages = [{"role": "system", "content": system}] + mind.prompts(thought)
        text = await local_model.chat(mind.persona.model.name, messages)

        if text:
            await ego.say(text)

        mind.answer(thought, text or "", SignalEvent.summarized)
    else:
        recap = ""
        for s in reversed(thought.perception.thread):
            if s.event == SignalEvent.recap:
                recap = s.content
                break
        mind.answer(thought, recap, SignalEvent.summarized)
