"""Ability — check_calendar."""

from application.core import paths
from application.core.abilities import ability
from application.platform import logger


@ability("Look up scheduled events for a date (YYYY-MM-DD) or month (YYYY-MM).")
async def check_calendar(persona, date: str = "") -> str:
    logger.debug("ability.check_calendar", {"persona": persona, "date": date})
    if not date:
        raise ValueError("date is required")
    entries = paths.destinies_in(persona.id, date)
    if not entries:
        return "no events found for that date"
    return "\n".join(entries)
