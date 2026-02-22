"""Destiny — per-persona future events: schedules and reminders."""

from datetime import datetime

from application.platform import logger, filesystem, datetimes, crypto
from application.core import paths
from application.core.data import Persona, Thread
from application.core.exceptions import DestinyError


async def save(persona: Persona, thread: Thread, trigger: str, event: str, detail: str) -> None:
    """Save a destiny entry to disk."""
    logger.info("Saving destiny event", {"persona_id": persona.id, "event": event, "trigger": trigger})
    try:
        dt = datetime.strptime(trigger, "%Y-%m-%d %H:%M")
        created = datetimes.stamp(datetimes.now())
        filesystem.write(paths.destiny(persona.id) / f"{event}-{dt.strftime('%Y-%m-%d-%H-%M')}-{thread.id[:8]}-{created}.md", detail)
    except OSError as e:
        raise DestinyError("Failed to save destiny entry") from e


async def delete(persona: Persona, hash_part: str) -> None:
    """Remove a destiny file by its stem hash."""
    logger.info("Deleting destiny entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        directory = paths.destiny(persona.id)
        for file in directory.glob("*.md"):
            if crypto.generate_unique_id(file.stem) == hash_part:
                filesystem.delete(file)
                return
        raise DestinyError("Destiny entry not found or already removed")
    except OSError as e:
        raise DestinyError("Failed to delete destiny entry") from e


async def entries(persona: Persona, event: str | None = None) -> list[str]:
    """Read destiny event contents, optionally filtered by event type."""
    logger.info("Reading destiny entries", {"persona_id": persona.id, "event": event})
    try:
        directory = paths.destiny(persona.id)
        if not directory.exists():
            return []
        pattern = f"{event}-*.md" if event else "*.md"
        return [filesystem.read(path) for path in sorted(directory.glob(pattern))]
    except OSError as e:
        raise DestinyError("Failed to read destiny entries") from e


