"""Brain — decide stage."""

from application.core import models
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import ModelError
from application.platform import logger


async def decide(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.decide", {"persona": persona, "meaning": memory.meaning})
    try:
        meaning_map = meanings.available(persona)
        meaning = meaning_map.get(memory.meaning)
        if not meaning:
            return False
        question = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"# ▶ YOUR TASK: {memory.meaning.capitalize()}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + meaning.prompt(persona)
        )
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
        if not isinstance(result, dict):
            return False
        memory.plan = result
        logger.debug("brain.decide plan", {"persona": persona, "plan": result, "reason": result.get("reason")})
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
    except ModelError as e:
        logger.warning("brain.decide failed", {"persona": persona, "meaning": memory.meaning, "error": str(e)})
        invalid = f"[invalid_json] Your previous response could not be parsed as JSON. Fix the issue or troubleshoot."
        memory.add(Message(
            content=invalid,
            prompt=Prompt(role="user", content=invalid),
        ))
        return False
    except Exception as e:
        logger.warning("brain.decide failed", {"persona": persona, "meaning": memory.meaning, "error": str(e)})
        return False
