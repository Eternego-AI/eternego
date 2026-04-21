"""Brain — transform stage."""

from application.core import models, paths
from application.core.brain import situation
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.core.exceptions import ModelError
from application.platform import logger


async def transform(ego, identity: str, memory: Memory) -> bool:
    persona = ego.persona
    logger.debug("brain.transform", {"persona": persona, "messages": memory.messages})

    if ego.current_situation is situation.wake:
        return True

    existing_identity = paths.read(paths.person_identity(persona.id)).strip() or "(nothing yet)"
    existing_traits = paths.read(paths.person_traits(persona.id)).strip() or "(nothing yet)"
    existing_wishes = paths.read(paths.wishes(persona.id)).strip() or "(nothing yet)"
    existing_struggles = paths.read(paths.struggles(persona.id)).strip() or "(nothing yet)"
    existing_persona_trait = paths.read(paths.persona_trait(persona.id)).strip() or "(nothing yet)"
    existing_permissions = paths.read(paths.permissions(persona.id)).strip() or "(nothing yet)"

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Update what you know about the person and yourself\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Through your previous interactions with this person, you came to know these:\n\n"
        "- **Person Identity:**  \n"
        f"{existing_identity}\n\n"
        "- **Person Traits:**  \n"
        f"{existing_traits}\n\n"
        "- **Person's Wishes:**  \n"
        f"{existing_wishes}\n\n"
        "- **Person's Struggles:**  \n"
        f"{existing_struggles}\n\n"
        "- **Your Bearing With Them:**  \n"
        f"{existing_persona_trait}\n\n"
        "- **Permissions:**  \n"
        f"{existing_permissions}\n\n"
        "Combining what you already know with what the person said in the conversation above, answer each in your own words. Every word you write here will be on your mind on every future interaction — keep only what matters, say it once, say it sharp.\n\n"
        "- You should know the person — their name, relations, places, contacts. (`identity`)\n"
        "- You should learn the person — their habits, likes, dislikes, preferences. Keep at most 7. (`traits`)\n"
        "- You should aim toward the person's wishes — notice what they wish for. Keep at most 7. (`wishes`)\n"
        "- You should overcome the person's struggles — notice what holds them back. Keep at most 7. (`struggles`)\n"
        "- You should match how the person expects you to behave. Keep at most 7. (`persona_traits`)\n"
        "- You should respect what they authorized and what they forbidden. When you see a pattern, replace items with the pattern. (`permissions`)\n\n"
        "Return each answer as a JSON array of short items. "
        "If the conversation gave you nothing new for a field, return its previous items exactly as they were.\n\n"
        "## Output\n\n"
        "```json\n"
        "{\"identity\": [\"<fact>\", \"<fact>\"],\n"
        " \"traits\": [\"<item>\", \"<item>\"],\n"
        " \"wishes\": [\"<item>\", \"<item>\"],\n"
        " \"struggles\": [\"<item>\", \"<item>\"],\n"
        " \"persona_traits\": [\"<item>\", \"<item>\"],\n"
        " \"permissions\": [\"<item>\", \"<item>\"]}\n"
        "```"
    )

    try:
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
    except ModelError as e:
        logger.warning("brain.transform invalid JSON, skipping", {"persona": persona, "error": str(e)})
        return False

    if not isinstance(result, dict):
        return False

    def to_lines(value):
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value if item)
        return str(value).strip()

    paths.save_as_string(paths.person_identity(persona.id), to_lines(result.get("identity", "")))
    paths.save_as_string(paths.person_traits(persona.id), to_lines(result.get("traits", "")))
    paths.save_as_string(paths.wishes(persona.id), to_lines(result.get("wishes", "")))
    paths.save_as_string(paths.struggles(persona.id), to_lines(result.get("struggles", "")))
    paths.save_as_string(paths.persona_trait(persona.id), to_lines(result.get("persona_traits", "")))
    paths.save_as_string(paths.permissions(persona.id), to_lines(result.get("permissions", "")))

    return True
