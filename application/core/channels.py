"""Channels — disk-backed verified channel list per persona. Gitignored so it resets on migration."""

from application.platform import logger, filesystem
from application.core.data import Persona
from application.core.exceptions import NetworkError


def _path(persona: Persona):
    return persona.storage_dir / "channels.md"


def _ensure(persona: Persona) -> None:
    path = _path(persona)
    if not path.exists():
        filesystem.write(path, "")


def is_verified(persona: Persona, network_id: str, chat_id: str) -> bool:
    """Return True if this chat_id is verified for the given network."""
    logger.info("Checking verified channel", {"persona": persona.id, "network": network_id})
    try:
        _ensure(persona)
        content = filesystem.read(_path(persona))
        entry = f"{network_id}:{chat_id}"
        return any(line.strip() == entry for line in content.splitlines())
    except OSError:
        return False


def add(persona: Persona, network_id: str, chat_id: str) -> None:
    """Mark a chat_id as verified for the given network. No-op if already verified."""
    logger.info("Adding verified channel", {"persona": persona.id, "network": network_id})
    try:
        _ensure(persona)
        if is_verified(persona, network_id, chat_id):
            return
        filesystem.append(_path(persona), f"{network_id}:{chat_id}\n")
    except OSError as e:
        raise NetworkError("Failed to save verified channel") from e


def all_for(persona: Persona, network_id: str) -> list[str]:
    """Return all verified chat_ids for the given network."""
    logger.info("Listing verified channels", {"persona": persona.id, "network": network_id})
    try:
        _ensure(persona)
        content = filesystem.read(_path(persona))
        prefix = f"{network_id}:"
        return [
            line.strip()[len(prefix):]
            for line in content.splitlines()
            if line.strip().startswith(prefix)
        ]
    except OSError:
        return []
