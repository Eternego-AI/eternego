"""Subconscious — extract and merge identity facts."""

from application.core import models, paths
from application.platform import logger


async def person_identity(persona, conversation: str) -> None:
    """Extract and merge identity facts."""
    logger.debug("subconscious.person_identity", {"persona": persona, "conversation": conversation})
    existing = paths.read(paths.person_identity(persona.id))
    system = (
        "# Extract Person's Identity Facts\n\n"
        "Read the conversation below. Extract concrete facts about the person.\n\n"
        "What counts:\n"
        "- Name, age, birthday, gender\n"
        "- Where they live\n"
        "- Job, employer, profession\n"
        "- Family: spouse, children, parents\n"
        "- Important contacts: doctors, close friends (include name, phone, address when given)\n"
        "- Strong long-term preferences they stated clearly\n\n"
        "Identity data should be relatively permanent and factual."
        "Only extract from what the person said (user messages).\n\n"
        f"## Current Facts\n\n{existing or '(none yet)'}\n\n"
        "Merge new facts into the list above. Keep everything that is still true. "
        "If the conversation adds nothing new, return the current facts unchanged.\n\n"
        "Format: one fact per line, each starting with 'The person '. "
        "No bullets, no headers, no commentary."
    )
    result = await models.chat(persona.thinking, [{"role": "system", "content": system}, {"role": "user", "content": conversation}])
    paths.save_as_string(paths.person_identity(persona.id), result.strip())
