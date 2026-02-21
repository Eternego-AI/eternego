"""Workspace — the persona's private sandbox for files, scripts, and notes."""

from application.platform import logger, filesystem
from application.core.data import Persona
from application.core.exceptions import IdentityError


async def create(persona: Persona) -> None:
    """Create the persona's workspace and notes directories."""
    logger.info("Creating workspace", {"persona_id": persona.id})
    try:
        filesystem.ensure_dir(persona.storage_dir / "workspace")
        filesystem.ensure_dir(persona.storage_dir / "notes")
    except OSError as e:
        raise IdentityError("Failed to create workspace") from e
