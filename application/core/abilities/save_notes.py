"""Ability — save_notes."""

from application.core import paths
from application.core.abilities import ability
from application.platform import logger


@ability(
    "Replace the persona's notes — the residue that doesn't fit anywhere "
    "else. Notes appear in the persona's identity on every interaction, so "
    "every line you write here gets re-read every beat. Use sparingly: notes "
    "are what's left when none of the structured stores fit."
)
async def save_notes(living, content: str = "") -> str:
    persona = living.ego.persona
    logger.debug("ability.save_notes", {"persona": persona, "content": content.strip()})
    if not content:
        raise ValueError("content is required")
    paths.save_as_string(paths.notes(persona.id), content.strip())
    return "notes updated"
