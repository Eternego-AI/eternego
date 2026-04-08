"""Subconscious — extract and merge struggles."""

from application.core import models, paths
from application.platform import logger


async def struggles(persona, conversation: str) -> None:
    """Extract and merge struggles."""
    logger.debug("subconscious.struggles", {"persona": persona, "conversation": conversation})
    existing = paths.read(paths.struggles(persona.id))
    system = (
        "# Extract Person's Struggles\n\n"
        "Read the conversation below. Extract difficulties or frustrations the person mentioned.\n\n"
        "What counts:\n"
        "- Problems they described clearly\n"
        "- Things that stress or frustrate them\n"
        "- Obstacles they are facing right now\n"
        "- Anything they said is hard for them\n\n"
        "Struggles are things the person is currently finding difficult. "
        "Only extract from what the person said (user messages).\n\n"
        f"## Current Struggles\n\n{existing or '(none yet)'}\n\n"
        "Merge new struggles into the list above. Keep everything that is still true. "
        "If the conversation adds nothing new, return the current struggles unchanged.\n\n"
        "Format: one struggle per line, each starting with 'The person '. "
        "No bullets, no headers, no commentary."
    )
    result = await models.chat(persona.thinking, [{"role": "system", "content": system}, {"role": "user", "content": conversation}])
    paths.save_as_string(paths.struggles(persona.id), result.strip())
