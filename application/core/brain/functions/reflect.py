"""Brain — reflect stage."""

from application.core import models
from application.core.brain import situation
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import ModelError
from application.platform import logger


async def reflect(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.reflect", {"persona": persona, "messages": memory.messages, "context": memory.context})

    if persona.ego and persona.ego.current_situation is situation.wake:
        return True

    existing = (memory.context or "").strip() or "(nothing yet)"
    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Reflect on your reality\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "The conversation above is your current reality. What do you want to remember from it? "
        "What did you experience? What would be worth telling yourself later, or keeping "
        "as a lesson learned?\n\n"
        "Do you see any unfinished duty, or anything worth investing time and resources "
        "to pick up and continue?\n\n"
        "## What you remembered last time\n\n"
        f"{existing}\n\n"
        "## Output\n\n"
        "Return JSON with two fields:\n"
        "- `context`: what you want to carry forward — combine what you remembered last time "
        "with what matters from this conversation. Drop what is resolved. Keep what is alive. "
        "Write it in your own words.\n"
        "- `leftover`: one short sentence naming what you want to continue right now, "
        "or `\"\"` if nothing calls for it.\n\n"
        "```json\n"
        "{\"context\": \"...\",\n"
        " \"leftover\": \"\"}\n"
        "```"
    )

    try:
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
    except ModelError as e:
        logger.warning("brain.reflect invalid JSON, skipping", {"persona": persona, "error": str(e)})
        return False

    if not isinstance(result, dict):
        return False

    context = str(result.get("context", "")).strip()
    leftover = str(result.get("leftover", "")).strip()

    memory.distill(context)
    logger.debug("brain.reflect result", {"persona": persona, "context": memory.context, "leftover": leftover})

    if leftover:
        seed_text = f"Return to: {leftover}"
        memory.remember(Message(
            content=seed_text,
            prompt=Prompt(role="user", content=seed_text),
        ))
        return False

    return True
