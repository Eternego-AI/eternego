"""Brain — reflect stage."""

from application.core import models
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


async def reflect(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.reflect", {"persona": persona, "messages": memory.messages, "context": memory.context})
    try:
        conversation = "\n".join(
            f"{'Person' if p['role'] == 'user' else 'Persona'}: {p['content']}"
            for p in memory.prompts
        )
        existing = memory.context or "(nothing yet)"
        system = (
            identity
            + "\n\n# Extract Context\n\n"
            "Extract what was discussed, what was decided, what is in progress, what is on "
            "the person's plate, reasons behind recent decisions, pending follow-ups, "
            "and anything the person or you committed to.\n\n"
            "This is operational context — recent, actionable, and likely to change soon. "
            "Do NOT include identity facts (name, job, contacts), behavioral traits, "
            "long-term wishes, or long-term struggles — those are extracted separately and "
            "persist independently.\n\n"
            "Combine new context with your previous extraction. Remove items that are clearly resolved. "
            "Keep what is still relevant."
        )
        result = await models.chat(persona.thinking, [
            {"role": "system", "content": system},
            {"role": "assistant", "content": existing},
            {"role": "user", "content": conversation},
        ])
        memory.context = result.strip()
        logger.debug("brain.reflect result", {"persona": persona, "context": memory.context})
        memory.clear()
        return True
    except Exception as e:
        logger.warning("brain.reflect failed", {"persona": persona, "error": str(e)})
        return False
