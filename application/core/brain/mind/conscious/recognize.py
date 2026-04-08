"""Conscious — experienced cognition: route, understand, and reply in one call."""

from application.core.brain.data import SignalEvent
from application.core.brain import perceptions
from application.core import bus, models
from application.platform import logger


async def recognize(memory, persona, meanings, identity_fn, say_fn, express_thinking_fn) -> None:
    """Experienced cognition: try to handle routing, understanding, and reply in one call.

    Sends current memory state, unattended signals, and meanings to the thinking
    model. Expects a new memory shape back. Writes directly to memory so realize,
    understand, and acknowledge find their work already done.
    """
    if not memory.needs_realizing:
        return

    logger.debug("Recognize", {"persona": persona})
    await bus.share("Pipeline: recognize", {"persona": persona, "stage": "recognize", "unattended": memory.needs_realizing})

    await express_thinking_fn()

    unattended = list(memory.needs_realizing)
    signal_index = {s.id: s for s in unattended}
    meaning_index = {m.name: m for m in meanings}

    existing_perceptions = "\n\n".join(
        f"- impression: \"{p.impression}\"\n  thread: {[s.id for s in p.thread]}"
        for p in memory.perceptions
    ) if memory.perceptions else "None"

    signals_text = "\n".join(
        f"- id: \"{s.id}\", event: \"{s.event}\", content: \"{s.content}\""
        for s in unattended
    )

    meanings_text = "\n".join(
        f"- {m.name}: {m.description()}"
        for m in meanings
    )

    system = (
        identity_fn()
        + "\n\n# Task: Recognize incoming signals\n"
        "You have new signals to process. Return a new memory shape that routes\n"
        "each signal into perceptions and matches them to meanings.\n\n"
        "A single signal may belong to multiple perceptions if it contains\n"
        "multiple intents (e.g. \"hello, remind me to call mom\" is both a\n"
        "greeting and a reminder request).\n\n"
        "## Current perceptions\n" + existing_perceptions + "\n\n"
        "## Unattended signals\n" + signals_text + "\n\n"
        "## Known meanings\n" + meanings_text + "\n\n"
        "## Response format\n"
        "Return JSON:\n"
        "{\n"
        '  "memory": {\n'
        '    "perceptions": [\n'
        '      {\n'
        '        "impression": "short topic description",\n'
        '        "thread": ["signal-id-1"]\n'
        '      }\n'
        '    ],\n'
        '    "thoughts": [\n'
        '      {\n'
        '        "perception": "matching impression text",\n'
        '        "meaning": "MeaningName",\n'
        '        "priority": 1\n'
        '      }\n'
        '    ]\n'
        '  },\n'
        '  "reply": "what to say to the person, or null"\n'
        "}\n\n"
        "Rules:\n"
        "- Use the exact signal IDs from the unattended signals list\n"
        "- Use exact meaning names from the known meanings list\n"
        "- Higher priority number = more important\n"
        "- Include existing perceptions that received new signals\n"
        "- Do NOT include existing perceptions that received no new signals\n"
        "- Do NOT state extracted values (dates, names, amounts) in the reply\n"
        "- If unsure about a meaning, omit the thought — the dedicated stage will handle it\n\n"
        "Reply guidelines:\n"
        "- If there is a request, acknowledge that you will handle it\n"
        "- If there is a conversation, respond naturally to what they said\n"
        "- You can combine responses across threads into one natural reply\n"
        "- Set reply to null only when signals are system events with no person-facing response"
    )

    messages = [{"role": "system", "content": system}, {"role": "user", "content": "Recognize each signal."}]
    result = await models.chat_json_stream(persona.thinking, messages)

    new_memory = result.get("memory", {})
    new_perceptions = new_memory.get("perceptions", [])
    new_thoughts = new_memory.get("thoughts", [])
    reply = result.get("reply")

    if not new_perceptions:
        return

    memory.accept_reality(new_perceptions, new_thoughts, signal_index, meaning_index)

    if reply:
        await say_fn(reply)
        for thought in memory.needs_acknowledgement:
            memory.answer(thought, reply, SignalEvent.answered)
            if not thought.meaning.path():
                memory.forget(thought)
