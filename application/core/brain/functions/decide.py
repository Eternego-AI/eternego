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
        logger.info("brain.decide chose prose, dispatching as say", {"persona": persona, "meaning": memory.meaning, "raw": e.raw})
        memory.remember(Message(content=e.raw, prompt=Prompt(role="assistant", content=e.raw)))
        dispatch(Command("Persona wants to say", {"persona": persona, "text": e.raw}))
        return True

    if not isinstance(result, dict):
        return False
    memory.plan = result
    logger.debug("brain.decide plan", {"persona": persona, "plan": result})
    if result.get("say") or result.get("tool") == "say":
        dispatch(Command("Persona wants to type", {"persona": persona}))
    return True
