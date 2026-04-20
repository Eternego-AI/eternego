"""Brain — recognize stage."""

from application.core import models
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import EngineConnectionError, ModelError
from application.platform import logger

from .escalate import escalate


async def recognize(persona: Persona, identity: str, memory: Memory) -> bool:
    meaning_map = memory.meanings
    meaning_names = list(meaning_map.keys())
    logger.debug("brain.recognize", {"persona": persona, "messages": memory.messages, "meanings_available": meaning_names})

    abilities = "\n".join(
        f"{i}. {meaning_map[name].intention()}"
        for i, name in enumerate(meaning_names, 1)
    )
    n = len(meaning_names)
    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Recognize what this moment calls for\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Considering the conversation:\n"
        "- What is your impression from the act that you would need to do?\n"
        "- Having the detected impression, which of the following abilities might resolve that?\n"
        "- If no ability can resolve the impression, return 0 as ability.\n"
        "## Abilities\n\n"
        + abilities + "\n\n"
        "## Output\n\n"
        "```json\n"
        '{"impression": "<your impression of the task at hand>",\n'
        f' "ability": <integer 0 to {n}>}}\n'
        "```"
    )

    try:
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
    except ModelError as e:
        invalid = "[invalid_json] Your previous response could not be parsed as JSON. Try again."
        logger.info("brain.recognize invalid JSON, seeding retry", {"persona": persona, "error": str(e)})
        memory.remember(Message(content=invalid, prompt=Prompt(role="user", content=invalid)))
        return False

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

    if not impression:
        logger.info("brain.recognize no impression, skipping escalation", {"persona": persona})
        struggle = "[no_impression] You could not form a clear impression of what to do. Try again with a clearer reading of the conversation."
        memory.remember(Message(content=struggle, prompt=Prompt(role="user", content=struggle)))
        return False

    logger.debug("brain.recognize escalating", {"persona": persona, "impression": impression, "meanings_available": meaning_names})
    meaning_name = await escalate(persona, memory, impression)
    if meaning_name:
        if meaning_name not in memory.meanings:
            learned = meanings.load(persona, meaning_name)
            if learned is not None:
                memory.learn(meaning_name, learned)
        memory.meaning = meaning_name
        return True

    struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
    memory.remember(Message(
        content=struggle,
        prompt=Prompt(role="user", content=struggle),
    ))
    return False
