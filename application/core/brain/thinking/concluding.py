"""Concluding — recaps and archives the most important finished Thought.

- Meaning had a path → collect a complete recap before sending.
  If interrupted by new signals, leave the thought for the next cycle.
- Either way → archive to history and forget.
"""

from application.core.data import Prompt
from application.core.brain import perceptions, signals
from application.core import channels, paths
from application.platform import logger


async def by(reply, mind) -> None:
    thought = mind.most_important_thought(mind.concluded)
    if not thought:
        return

    persona = mind.persona
    logger.info("concluding.by", {"impression": thought.perception.impression})

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
            mind.answer(thought, recap)

    thread_text = perceptions.thread(thought.perception)
    paths.add_history_entry(persona.id, thought.perception.impression, thread_text)
    mind.forget(thought)
