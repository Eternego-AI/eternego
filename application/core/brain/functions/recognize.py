"""Brain — recognize stage."""

from application.core import models
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.platform import logger

from .escalate import escalate


async def recognize(persona: Persona, identity: str, memory: Memory) -> bool:
    meaning_map = meanings.available(persona)
    meaning_names = list(meaning_map.keys())
    logger.debug("brain.recognize", {"persona": persona, "messages": memory.messages, "meanings_available": meaning_names})

    try:
        abilities = "\n".join(
            f"{i}. {meaning_map[name].intention(persona)}"
            for i, name in enumerate(meaning_names, 1)
        )
        n = len(meaning_names)
        question = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "# ▶ YOUR TASK: Recognize what this moment calls for\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Pick the ability — from the list below — that fits what the conversation now needs. "
            f"The need may be a reply to what was just said, a continuation of a thread you were on, "
            f"or an action you're choosing to take. Match by capability, not by topic. Return 0 when "
            f"no listed ability can actually do what is needed (e.g. anything requiring shell, live "
            f"system state, the web, or external services not listed).\n\n"
            "## Abilities\n\n"
            + abilities + "\n\n"
            "## Output\n\n"
            "```json\n"
            '{"impression": "<what do you think is happening>",\n'
            f' "ability": <integer 0 to {n}>}}\n'
            "```"
        )
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
        impression = ""
        if isinstance(result, dict):
            impression = str(result.get("impression", "")).strip()
            raw = result.get("ability", 0)
            try:
                idx = int(raw)
            except (TypeError, ValueError):
                if isinstance(raw, str):
                    match = raw.strip().lower()
                    for name in meaning_names:
                        if name == match or name.startswith(match):
                            memory.meaning = name
                            logger.debug("brain.recognize selected", {"persona": persona, "meaning": memory.meaning})
                            return True
                idx = 0
            if 1 <= idx <= len(meaning_names):
                memory.meaning = meaning_names[idx - 1]
                logger.debug("brain.recognize selected", {"persona": persona, "meaning": memory.meaning})
                return True
    except Exception as e:
        logger.warning("brain.recognize matching failed", {"persona": persona, "error": str(e), "meanings_available": meaning_names})
        impression = ""

    logger.debug("brain.recognize escalating", {"persona": persona, "impression": impression, "meanings_available": meaning_names})
    impression = impression or "The persona could not match any existing ability to what was needed."
    meaning_name = await escalate(persona, impression)
    if meaning_name:
        memory.meaning = meaning_name
        return True

    struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
    memory.add(Message(
        content=struggle,
        prompt=Prompt(role="user", content=struggle),
    ))
    return False
