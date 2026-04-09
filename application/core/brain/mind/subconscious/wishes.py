"""Subconscious — extract and merge wishes and aspirations."""

from application.core import models, paths
from application.platform import logger


async def wishes(persona, conversation: str) -> None:
    """Extract and merge wishes and aspirations."""
    logger.debug("subconscious.wishes", {"persona": persona, "conversation": conversation})
    existing = paths.read(paths.wishes(persona.id))
    system = (
        "# Extract Person's Wishes and Dreams\n\n"
        "Read the conversation below. Extract what the person wants in life — "
        "their goals, dreams, and things they care deeply about.\n\n"
        "What counts:\n"
        "- Goals they mentioned: career, personal, creative\n"
        "- Things they said they want to build, achieve, or change\n"
        "- Values they expressed with conviction\n"
        "- Directions they are clearly moving toward\n\n"
        "Wishes are things the person aspires to or deeply cares about. "
        "They may be long-term or short-term, but they indicate what the person wants in life. "
        "Only extract from what the person said (user messages).\n\n"
        f"## Current Wishes\n\n{existing or '(none yet)'}\n\n"
        "Merge new wishes into the list above. Keep everything that is still true. "
        "If the conversation adds nothing new, return the current wishes unchanged.\n\n"
        "Format: one wish per line, each starting with 'The person '. "
        "No bullets, no headers, no commentary."
    )
    result = await models.chat(persona.thinking, [{"role": "system", "content": system}, {"role": "user", "content": conversation}])
    paths.save_as_string(paths.wishes(persona.id), result.strip())
