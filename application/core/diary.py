"""Diary — persona backup, encryption, and versioning."""

import subprocess
import zipfile
from pathlib import Path

from cryptography.fernet import InvalidToken

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


async def open(diary_path: str, phrase: str) -> Path:
    """Decrypt and unzip a diary entry, return path to the contents."""
    path = Path(diary_path)
    persona_id = path.stem
    logger.info("Opening diary entry", {"persona_id": persona_id})
    try:
        encrypted = filesystem.read_bytes(path)
        key = crypto.derive_key(phrase, salt=persona_id.encode())
        archive = crypto.decrypt(encrypted, key)
        staging = DIARY_DIR / persona_id / "staging"
        filesystem.unzip(archive, staging)
        return staging
    except InvalidToken as e:
        raise DiaryError("Failed to decrypt diary entry — check your recovery phrase") from e
    except (OSError, zipfile.BadZipFile) as e:
        raise DiaryError("Failed to open diary entry") from e


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
