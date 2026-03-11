"""Wondering — generates a streaming reply for the most important unanswered Thought.

Streams a reply paragraph by paragraph. After streaming:
- Meaning has no path → thought is marked resolved (done)
- Meaning has a path  → thought stays open; deciding will execute the action
"""

from application.core.data import Prompt
from application.core.brain import signals
from application.core import channels
from application.platform import logger


async def by(reply, mind) -> None:
    thought = mind.most_important_thought(mind.unanswered)
    if not thought:
        return

    persona = mind.persona
    logger.info("wondering.by", {"impression": thought.perception.impression})

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
        if mind.changed():
            if text:
                mind.answer(thought, text)
            return
        if channel:
            await channels.send(channel, paragraph)
        text += ("\n" if text else "") + paragraph

    if text:
        mind.answer(thought, text)

    if not thought.meaning.path():
        mind.resolve(thought)
