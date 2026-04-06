"""Conscious — the waking thinking pipeline.

Five functions, each receiving exactly what it needs:
  realize → understand → recognize → decide → conclude
"""

import uuid

from application.core.brain.data import Signal, SignalEvent
from application.core.brain import perceptions, signals
from application.core import bus, channels, local_model
from application.platform import logger


def document() -> str:
    """Return a description of persona consciousness for model prompts.

    WARNING: This document is used in escalation prompts to teach models how
    meanings work in the conscious sequence. If you change how realize, understand,
    recognize, decide, or conclude use meaning methods, update this document
    to match. Out-of-sync documentation leads to broken generated meanings.
    """
    return (
        "Persona consciousness works as a continuous loop of five stages:\n"
        "  realize → understand → recognize → decide → conclude\n\n"
        "When a person sends a message, it arrives as a signal. The consciousness\n"
        "processes it through these stages, and if new input arrives at any point,\n"
        "it restarts from the beginning — the persona is always responsive.\n\n"
        "**realize** — Each signal gets an impression — a short description of what\n"
        "  the conversation is about. Signals with the same impression form a thread.\n\n"
        "**understand** — The thread's impression is matched against known meanings.\n"
        "  Each meaning has a name and description. The model picks the best match.\n"
        "  When nothing matches, escalation creates a new meaning.\n\n"
        "**recognize** — The meaning's reply() prompt guides the first response to\n"
        "  the person. If the previous action failed, clarify() guides a retry.\n"
        "  CRITICAL: The reply becomes visible to the decide step. Never state\n"
        "  extracted values in the reply — errors propagate into extraction.\n\n"
        "**decide** — The meaning's path() prompt tells the model what to extract.\n"
        "  The model returns JSON. For tool use: {\"tool\": \"tool_name\", ...params}.\n"
        "  The default run() dispatches the tool call automatically. Results flow\n"
        "  back into the thread as executed signals.\n\n"
        "**conclude** — The meaning's summarize() prompt generates a final message\n"
        "  confirming what was done. The thought is then complete."
    )


# ── Realizing ─────────────────────────────────────────────────────────────────

async def realize(memory, persona, identity_fn) -> None:
    """Route unattended signals to existing or new perception threads."""
    if not memory.needs_realizing:
        return

    logger.debug("Realize", {"persona": persona})
    await bus.share("Pipeline: realize", {"persona": persona, "stage": "realize", "unattended": len(memory.needs_realizing)})

    await channels.express_thinking(persona)

    known = memory.perceptions
    thread_map = {i + 1: p for i, p in enumerate(known)}
    unattended = list(memory.needs_realizing)
    signal_map = {i + 1: s for i, s in enumerate(unattended)}

    threads_text = "\n\n".join(
        f"{i}. {p.impression}\n{perceptions.conversation(p)}"
        for i, p in thread_map.items()
    ) if known else "None"

    signals_text = "\n".join(
        f"{i}. {signals.labeled(s)}"
        for i, s in signal_map.items()
    )

    system = (
        identity_fn()
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
    result = await local_model.chat_json_stream(persona.model.name, messages)
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
                memory.realize(signal, perception.impression)

        for impression in route.get("new_impressions", []):
            if impression:
                memory.realize(signal, impression)

        if not route.get("threads") and not route.get("new_impressions"):
            logger.warning("realize: route with no threads or impressions", {"signal_id": signal.id})

    for signal in unattended:
        if signal.id not in routed:
            logger.warning("realize: unrouted signal, stays unattended", {"signal_id": signal.id})


# ── Understanding ────────────────────────────────────────────────────────────

async def understand(memory, persona, meanings, identity_fn, escalate_fn) -> None:
    """Match the most important unrecognized perception to a meaning."""
    perception = memory.most_important_perception
    if not perception:
        return

    logger.debug("Understand", {"persona": persona, "impression": perception.impression})
    await bus.share("Pipeline: understand", {"persona": persona, "stage": "understand", "impression": perception.impression})

    await channels.express_thinking(persona)

    meanings_text = "\n".join(
        f"{i + 1}. {m.name}: {m.description()}"
        for i, m in enumerate(meanings)
    )

    system = (
        identity_fn()
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
    result = await local_model.chat_json_stream(persona.model.name, messages)
    row = result.get("meaning_row")

    escalation = next(m for m in meanings if m.name == "Escalation")
    if isinstance(row, (int, float)) and 1 <= int(row) <= len(meanings):
        meaning = meanings[int(row) - 1]
    else:
        meaning = escalation

    # Escalation → try generating a new meaning via frontier/local model
    if meaning.name == "Escalation":
        from application.core.brain.mind import meanings as meanings_module
        code = await escalate_fn(perceptions.thread(perception), meanings)
        if code:
            try:
                new_meaning = meanings_module.learn(persona, code)
                meanings.append(new_meaning)
                meaning = new_meaning
            except Exception as e:
                logger.error("understand: failed to learn meaning", {"persona": persona, "error": str(e)})

    memory.understand(perception, meaning)


# ── Recognition ──────────────────────────────────────────────────────────────

async def recognize(memory, persona, identity_fn, say_fn) -> None:
    """Generate a reply for the most important thought that needs recognition."""
    thought = memory.most_important_thought(memory.needs_recognition)
    if not thought:
        return

    await channels.express_thinking(persona)

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

    logger.debug("Recognize", {"persona": persona, "impression": thought.perception.impression, "event": event})
    await bus.share("Pipeline: recognize", {"persona": persona, "stage": "recognize", "impression": thought.perception.impression, "meaning": thought.meaning.name})

    await channels.express_thinking(persona)

    system = identity_fn() + "\n\n# This Interaction\n" + "\n".join(filter(None, [
        m.description(),
        prompt,
    ]))

    messages = [{"role": "system", "content": system}] + memory.prompts(thought)
    text = await local_model.chat(persona.model.name, messages)

    if text:
        await say_fn(text)
        memory.answer(thought, text, event)

    if not m.path():
        memory.forget(thought)


# ── Deciding ─────────────────────────────────────────────────────────────────

async def decide(memory, persona, identity_fn) -> None:
    """Execute the action for the most important pending thought."""
    import json

    thought = memory.most_important_thought(memory.needs_decision)
    if not thought:
        return

    await channels.express_thinking(persona)

    logger.debug("Decide", {"persona": persona, "impression": thought.perception.impression})
    await bus.share("Pipeline: decide", {"persona": persona, "stage": "decide", "impression": thought.perception.impression, "meaning": thought.meaning.name})

    system = (
        identity_fn()
        + "\n\n" + thought.meaning.path()
        + "\n\nAdd a \"recap\" field to your JSON — one sentence on what you did or are doing.\n"
        "If already fulfilled, return just: {\"recap\": \"what was accomplished\"}."
    )
    messages = [{"role": "system", "content": system}] + memory.prompts(thought)
    result = await local_model.chat_json_stream(persona.model.name, messages)
    recap = result.pop("recap", None) if isinstance(result, dict) else None

    if not result:
        memory.answer(thought, recap or "", SignalEvent.recap)
        return

    decision_text = json.dumps(result)
    memory.answer(thought, decision_text, SignalEvent.decided)

    try:
        action = await thought.meaning.run(result)
    except Exception as e:
        logger.error("Decide: run failed", {"persona": persona, "error": str(e)})
        memory.inform(thought, Signal(
            id=str(uuid.uuid4()), event=SignalEvent.executed,
            content=f"[{thought.meaning.name}: {decision_text}] Error: {e}",
        ))
        return

    if action is None:
        memory.answer(thought, recap or "", SignalEvent.recap)
        return

    try:
        output = await action()
    except Exception as e:
        logger.error("Decide: action failed", {"persona": persona, "error": str(e)})
        output = f"Error: {e}"

    if output is not None:
        content = f"[{thought.meaning.name}: {decision_text}]"
        if output:
            content += f" {output}"
        memory.inform(thought, Signal(
            id=str(uuid.uuid4()), event=SignalEvent.executed,
            content=content,
        ))
    else:
        memory.answer(thought, recap or "", SignalEvent.recap)


# ── Concluding ───────────────────────────────────────────────────────────────

async def conclude(memory, persona, identity_fn, say_fn) -> None:
    """Summarize for the person and mark the thought as concluded."""
    thought = memory.most_important_thought(memory.needs_conclusion)
    if not thought:
        return

    await channels.express_thinking(persona)

    logger.debug("Conclude", {"persona": persona, "impression": thought.perception.impression})
    await bus.share("Pipeline: conclude", {"persona": persona, "stage": "conclude", "impression": thought.perception.impression, "meaning": thought.meaning.name})

    summary_prompt = thought.meaning.summarize()
    if summary_prompt:
        await channels.express_thinking(persona)

        system = identity_fn() + "\n\n# This Interaction\n" + "\n".join(filter(None, [
            thought.meaning.description(),
            summary_prompt,
        ]))
        messages = [{"role": "system", "content": system}] + memory.prompts(thought)
        text = await local_model.chat(persona.model.name, messages)

        if text:
            await say_fn(text)

        memory.answer(thought, text or "", SignalEvent.summarized)
    else:
        recap = ""
        for s in reversed(thought.perception.thread):
            if s.event == SignalEvent.recap:
                recap = s.content
                break
        memory.answer(thought, recap, SignalEvent.summarized)
