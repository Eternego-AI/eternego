"""Brain — realize stage."""

from application.core.brain.mind.memory import Memory
from application.core.data import Persona, Prompt
from application.platform import logger


async def realize(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.realize", {"persona": persona, "messages": memory.messages})
    for m in memory.messages:
        if m.prompt is None:
            m.prompt = Prompt(role="user", content=m.content)
    return bool(memory.messages)
