"""Concluding — recaps and archives the most important finished Thought.

- Meaning had a path → stream a recap, save it to the thread.
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

    recap = ""

    if thought.meaning.path():
        channel = channels.latest(persona) or channels.default_channel(persona)
        system = (
            "Generate a brief, natural recap of what was accomplished in this conversation. "
            "Be concise — one or two sentences."
        )
        prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

        async for paragraph in reply(persona, system, prompts):
            if mind.changed():
                break
            if channel:
                await channels.send(channel, paragraph)
            recap += ("\n" if recap else "") + paragraph

        if recap:
            mind.answer(thought, recap)

    thread_text = perceptions.thread(thought.perception)
    content = thread_text
    paths.add_history_entry(persona.id, thought.perception.impression, content)
    mind.forget(thought)
