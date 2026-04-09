"""Conscious — generate a reply for the person."""

from application.core.brain.data import SignalEvent
from application.core import bus, models
from application.platform import logger


async def acknowledge(memory, persona, identity_fn, say_fn, express_thinking_fn) -> None:
    """Generate a reply for the most important thought that needs acknowledgement."""
    thought = memory.most_important_thought(memory.needs_acknowledgement)
    if not thought:
        return

    await express_thinking_fn()

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

    logger.debug("Acknowledge", {"persona": persona, "impression": thought.perception.impression, "event": event})
    await bus.share("Pipeline: acknowledge", {"persona": persona, "stage": "acknowledge", "impression": thought.perception.impression, "meaning": thought.meaning.name})

    system = identity_fn() + "\n\n# This Interaction\n" + "\n".join(filter(None, [
        m.description(),
        prompt,
    ]))

    messages = [{"role": "system", "content": system}] + memory.prompts(thought)
    text = await models.chat(persona.thinking, messages)

    if text:
        await say_fn(text)
        memory.answer(thought, text, event)

    if not m.path():
        memory.forget(thought)
