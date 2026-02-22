"""Destiny — per-persona future events: schedules and reminders."""

from datetime import datetime

from application.platform import logger, filesystem, datetimes
from application.core import paths
from application.core.data import Persona
from application.core.exceptions import IdentityError


async def save(persona: Persona, trigger: str, event: str, detail: str) -> None:
    """Save a destiny event to disk."""
    logger.info("Saving destiny event", {"persona_id": persona.id, "event": event, "trigger": trigger})
    try:
        dt = datetime.strptime(trigger, "%Y-%m-%d %H:%M")
        created = datetimes.stamp(datetimes.now())
        filesystem.write(paths.destiny(persona.id) / f"{event}-{dt.strftime('%Y-%m-%d-%H-%M')}-{created}.md", detail)
    except OSError as e:
        raise IdentityError("Failed to save destiny event") from e


async def read(persona: Persona, event: str | None = None) -> list[str]:
    """Read destiny event contents, optionally filtered by event type."""
    logger.info("Reading destiny events", {"persona_id": persona.id, "event": event})
    try:
        directory = paths.destiny(persona.id)
        if not directory.exists():
            return []
        pattern = f"{event}-*.md" if event else "*.md"
        return [filesystem.read(path) for path in sorted(directory.glob(pattern))]
    except OSError as e:
        raise IdentityError("Failed to read destiny events") from e


