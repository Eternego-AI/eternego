"""Brain — decide stage."""

from application.core import models
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


async def decide(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.decide", {"persona": persona, "meaning": memory.meaning})
    try:
        meaning_map = meanings.available(persona)
        meaning = meaning_map.get(memory.meaning)
        if not meaning:
            return False
        system = (
            identity
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"# ▶ YOUR TASK: {memory.meaning.capitalize()}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + meaning.prompt(persona)
        )
        prompt = [{"role": "system", "content": system}] + memory.prompts
        result = await models.chat_json(persona.thinking, prompt)
        if not isinstance(result, dict):
            return False
        memory.plan = result
        logger.debug("brain.decide plan", {"persona": persona, "plan": result})
        if result.get("say") or result.get("tool") == "say":
            from application.platform import telegram
            active = persona.ego.channels if persona.ego else []
            for channel in active:
                if channel.type == "telegram":
                    try:
                        token = (channel.credentials or {})["token"]
                        await telegram.async_typing_action(token, channel.name)
                    except Exception:
                        pass
        return True
    except Exception as e:
        logger.warning("brain.decide failed", {"persona": persona, "meaning": memory.meaning, "error": str(e)})
        return False
