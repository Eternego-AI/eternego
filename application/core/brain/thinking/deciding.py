"""Deciding — executes the action for the most important pending Thought.

Takes the highest-priority pending Thought (lowest order), calls meaning.run(),
and either resolves it or feeds the result back into the thread. The tick loop
handles returning to deciding if more pending thoughts remain.
"""

from application.core.data import Prompt
from application.core.brain import signals
from application.platform import logger


async def by(reason, mind) -> None:
    thought = mind.most_important_thought(mind.pending)
    if not thought:
        return

    persona = mind.persona
    logger.info("deciding.by", {"impression": thought.perception.impression, "order": thought.order})

    system = thought.meaning.path()
    prompts = [Prompt(role=s.role, content=signals.as_chat(s)) for s in thought.perception.thread]

    result = await reason(persona, system, prompts)

    signal = await thought.meaning.run(result)

    if signal is None:
        mind.resolve(thought)
    else:
        mind.inform(thought, signal)
