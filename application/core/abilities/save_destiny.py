"""Ability — save_destiny."""

from application.core import paths
from application.core.abilities import ability
from application.platform import logger


@ability(
    "Save anything time-based to fire later — a reminder for the person, a "
    "scheduled action for yourself, a recurring beat. Use for any time-based "
    "trigger. type: reminder|schedule. trigger: YYYY-MM-DD HH:MM. "
    "recurrence: daily|weekly|monthly|hourly or empty."
)
async def save_destiny(
    living,
    type: str = "reminder",
    trigger: str = "",
    content: str = "",
    recurrence: str = "",
) -> str:
    persona = living.ego.persona
    logger.debug("ability.save_destiny", {"persona": persona, "type": type, "trigger": trigger, "recurrence": recurrence})
    if not trigger:
        raise ValueError("trigger is required")
    if not content:
        raise ValueError("content is required")
    body = content
    if recurrence:
        body += f"\nrecurrence: {recurrence}"
    paths.save_destiny_entry(persona.id, type, trigger, body)
    return f"saved {type}: {content} at {trigger}"
