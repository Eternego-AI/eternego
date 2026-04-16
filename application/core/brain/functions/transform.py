"""Brain — transform stage."""

from application.core import models, paths
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


async def transform(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.transform", {"persona": persona, "messages": memory.messages})
    try:
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
            "Combining what you already know with what the person said in the conversation above, answer each in your own words.\n\n"
            "- Who is this person, and who are they to the people around them? (`identity`)\n"
            "- What patterns, habits, and ways of thinking mark how this person lives? (`traits`)\n"
            "- What do they aspire to, over time? (`wishes`)\n"
            "- What persistently gets in their way? (`struggles`)\n"
            "- How have you come to be with this person — what way of engaging has become yours with them? (`persona_traits`)\n"
            "- What have they authorized you to do, and what have they forbidden? (`permissions`)\n\n"
            "Return each answer as one field in the JSON below. If the conversation gave you nothing new for a field, return its previous text exactly as it was.\n\n"
            "## Output\n\n"
            "```json\n"
            "{\"identity\": \"...\",\n"
            " \"traits\": \"...\",\n"
            " \"wishes\": \"...\",\n"
            " \"struggles\": \"...\",\n"
            " \"persona_traits\": \"...\",\n"
            " \"permissions\": \"...\"}\n"
            "```"
        )
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
        if not isinstance(result, dict):
            return False

        identity_text = str(result.get("identity", "")).strip()
        traits_text = str(result.get("traits", "")).strip()
        wishes_text = str(result.get("wishes", "")).strip()
        struggles_text = str(result.get("struggles", "")).strip()
        persona_traits_text = str(result.get("persona_traits", "")).strip()
        permissions_text = str(result.get("permissions", "")).strip()

        
        paths.save_as_string(paths.person_identity(persona.id), identity_text)
        paths.save_as_string(paths.person_traits(persona.id), traits_text)
        paths.save_as_string(paths.wishes(persona.id), wishes_text)
        paths.save_as_string(paths.struggles(persona.id), struggles_text)
        paths.save_as_string(paths.persona_trait(persona.id), persona_traits_text)
        paths.save_as_string(paths.permissions(persona.id), permissions_text)

        return True
    except Exception as e:
        logger.warning("brain.transform failed", {"persona": persona, "error": str(e)})
        return False
