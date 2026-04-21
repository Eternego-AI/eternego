"""Brain — decide stage."""

from application.core import models
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import EngineConnectionError, ModelError
from application.platform import logger
from application.platform.observer import Command, dispatch


async def decide(ego, identity: str, memory: Memory) -> bool:
    persona = ego.persona
    logger.debug("brain.decide", {"persona": persona, "meaning": memory.meaning})
    meaning = memory.meanings.get(memory.meaning)
    if not meaning:
        return False
    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"# ▶ YOUR TASK: {memory.meaning.capitalize()}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        + meaning.prompt()
    )

    try:
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
    except ModelError as e:
        logger.warning("brain.decide invalid JSON, seeding retry", {"persona": persona, "meaning": memory.meaning, "error": str(e)})
        invalid = "[invalid_json] Your previous response could not be parsed as JSON. Fix the issue or troubleshoot."
        memory.remember(Message(
            content=invalid,
            prompt=Prompt(role="user", content=invalid),
        ))
        return False

    if not isinstance(result, dict):
        return False
    memory.plan = result
    logger.debug("brain.decide plan", {"persona": persona, "plan": result, "reason": result.get("reason")})
    if result.get("say") or result.get("tool") == "say":
        dispatch(Command("Persona wants to type", {"persona": persona, "channel_type": "telegram"}))
    return True
