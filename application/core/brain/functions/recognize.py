"""Brain — recognize stage."""

from application.core import models
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Prompt
from application.core.exceptions import BrainException, ModelError
from application.platform import logger
from application.platform.observer import Command, dispatch


async def recognize(ego, identity: str, memory: Memory) -> bool:
    persona = ego.persona
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
        logger.info("brain.recognize chose prose, dispatching as say", {"persona": persona, "raw": e.raw})
        memory.remember(Message(content=e.raw, prompt=Prompt(role="assistant", content=e.raw)))
        dispatch(Command("Persona wants to say", {"persona": persona, "text": e.raw}))
        if memory.meaning == "troubleshooting":
            logger.warning("brain.recognize refused while on troubleshooting — raising thinking fault", {"persona": persona})
            raise BrainException(
                "thinking model refused classification while on troubleshooting",
                model=persona.thinking,
            ) from e
        if "troubleshooting" in meaning_map:
            memory.impression = "could not classify the moment; forcing self-diagnosis"
            memory.meaning = "troubleshooting"
            memory.ability = meaning_names.index("troubleshooting") + 1
            logger.info("brain.recognize forcing troubleshooting after prose", {"persona": persona})
            return True
        memory.impression = ""
        memory.ability = 0
        memory.meaning = None
        return False

    if not isinstance(result, dict):
        memory.impression = ""
        memory.ability = 0
        return False

    memory.impression = str(result.get("impression", "")).strip()
    raw = result.get("ability", 0)
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        if isinstance(raw, str):
            match = raw.strip().lower()
            for i, name in enumerate(meaning_names, 1):
                if name == match or name.startswith(match):
                    memory.ability = i
                    memory.meaning = name
                    logger.debug("brain.recognize selected", {"persona": persona, "meaning": memory.meaning})
                    return True
        idx = 0

    if 1 <= idx <= len(meaning_names):
        memory.ability = idx
        memory.meaning = meaning_names[idx - 1]
        logger.debug("brain.recognize selected", {"persona": persona, "meaning": memory.meaning})
        return True

    memory.ability = 0
    memory.meaning = None
    return True
