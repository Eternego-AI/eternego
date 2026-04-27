"""Ability — save_notes."""

from application.core import paths
from application.core.abilities import ability
from application.platform import logger


@ability("Replace the persona's notes with the given content. Notes appear in the persona's identity on every interaction.")
async def save_notes(persona, content: str = "") -> str:
    logger.debug("ability.save_notes", {"persona": persona, "content": content.strip()})
    if not content:
        raise ValueError("content is required")
    paths.save_as_string(paths.notes(persona.id), content.strip())
    return "notes updated"
