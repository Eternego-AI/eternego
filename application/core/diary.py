"""Diary — persona backup, encryption, and versioning."""

import subprocess
from pathlib import Path

from application.platform import logger, filesystem, crypto, git
from application.core.data import Persona
from application.core.exceptions import DiaryError


DIARY_DIR = Path.home() / ".eternego" / "diary"


async def open_for(persona: Persona) -> None:
    """Create a diary directory for the persona and initialize git."""
    logger.info("Opening diary", {"persona_id": persona.id})
    try:
        path = DIARY_DIR / persona.id
        filesystem.ensure_dir(path)
        git.init(path)
    except (OSError, subprocess.CalledProcessError) as e:
        raise DiaryError("Failed to initialize diary") from e


async def record(memory_path: Path, phrase: str) -> None:
    """Zip the persona directory, encrypt it, save to diary, and git commit."""
    persona_id = memory_path.name
    logger.info("Recording diary entry", {"persona_id": persona_id})
    try:
        archive = filesystem.zip(memory_path)
        key = crypto.derive_key(phrase, salt=persona_id.encode())
        encrypted = crypto.encrypt(archive, key)
        diary_path = DIARY_DIR / persona_id
        entry_path = diary_path / f"{persona_id}.zip"
        filesystem.write_bytes(entry_path, encrypted)
        git.add(diary_path, f"{persona_id}.zip")
        git.commit(diary_path, "Diary entry")
    except (OSError, subprocess.CalledProcessError) as e:
        raise DiaryError("Failed to record diary entry") from e
