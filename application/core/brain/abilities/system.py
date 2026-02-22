"""System abilities — executing system commands."""

from application.platform import logger
from application.core.data import Channel, Persona, Prompt, Thread
from application.core.brain.abilities._base import ability


@ability(
"Execute system commands. Items: [{function: {name, arguments: {command}}}]",
["commander"],
order=6)
async def act(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Execute tool calls and return the result so the model can respond."""
    logger.info("Ability: act", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.core import system
    result = await system.execute(items)
    return Prompt(role="user", content=f"Result:\n{result}")
