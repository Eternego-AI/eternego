"""History — long-term conversation history for a persona."""

from application.platform import logger, filesystem, crypto
from application.core.data import Persona
from application.core.exceptions import IdentityError


async def start(persona: Persona) -> None:
    """Create the history directory for a new persona."""
    logger.info("Starting history", {"persona_id": persona.id})
    try:
        filesystem.ensure_dir(persona.storage_dir / "history")
    except OSError as e:
        raise IdentityError("Failed to start history") from e


async def entries(persona: Persona) -> list[str]:
    """Read the agent's conversation history names."""
    logger.info("Reading history entries", {"persona_id": persona.id})
    try:
        names = []
        history_dir = persona.storage_dir / "history"
        if history_dir.exists():
            for file in sorted(history_dir.glob("*")):
                names.append(file.stem)
        return names
    except OSError as e:
        raise IdentityError("Failed to read history entries") from e


async def recall(persona: Persona) -> str:
    """Read all history files and return concatenated conversations."""
    logger.info("Recalling history", {"persona_id": persona.id})
    try:
        parts = []
        history_dir = persona.storage_dir / "history"
        if history_dir.exists():
            for file in sorted(history_dir.glob("*")):
                parts.append(filesystem.read(file))
        return "\n\n---\n\n".join(parts)
    except OSError as e:
        raise IdentityError("Failed to read history") from e


async def delete(persona: Persona, hash_part: str) -> None:
    """Remove a conversation file from history by its name hash."""
    logger.info("Deleting history entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        history_dir = persona.storage_dir / "history"
        for file in history_dir.glob("*"):
            if crypto.generate_unique_id(file.stem) == hash_part:
                filesystem.delete(file)
                return
        raise IdentityError("History entry not found or already removed")
    except OSError as e:
        raise IdentityError("Failed to delete history entry") from e
