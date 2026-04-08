"""Conscious — summarize and complete a thought."""

from application.core.brain.data import SignalEvent
from application.core import bus, models
from application.platform import logger


async def conclude(memory, persona, identity_fn, say_fn, express_thinking_fn) -> None:
    """Summarize for the person and mark the thought as concluded."""
    thought = memory.most_important_thought(memory.needs_conclusion)
    if not thought:
        return

    await express_thinking_fn()

    logger.debug("Conclude", {"persona": persona, "impression": thought.perception.impression})
    await bus.share("Pipeline: conclude", {"persona": persona, "stage": "conclude", "impression": thought.perception.impression, "meaning": thought.meaning.name})

    summary_prompt = thought.meaning.summarize()
    if summary_prompt:
        await express_thinking_fn()

        system = identity_fn() + "\n\n# This Interaction\n" + "\n".join(filter(None, [
            thought.meaning.description(),
            summary_prompt,
        ]))
        messages = [{"role": "system", "content": system}] + memory.prompts(thought)
        text = await models.chat(persona.thinking, messages)

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
