"""System — generic program availability and installation."""

import subprocess

from application.platform import logger, OS, linux, mac, windows
from application.core import local_model
from application.core.data import Persona
from application.core.exceptions import UnsupportedOS, InstallationError, SecretStorageError


async def is_installed(program: str) -> bool:
    """Check if a program is installed on the current OS."""
    logger.info("Checking if program is installed", {"program": program})
    platform = OS.get_supported()

    if platform == "linux":
        return await linux.is_installed(program)
    if platform == "mac":
        return await mac.is_installed(program)
    if platform == "windows":
        return await windows.is_installed(program)

    raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")


async def install(program: str) -> None:
    """Install a program on the current OS."""
    logger.info("Installing program", {"program": program})
    platform = OS.get_supported()

    if platform is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")

    try:
        if platform == "linux":
            await linux.install(program)
        elif platform == "mac":
            await mac.install(program)
        elif platform == "windows":
            await windows.install(program)
    except (subprocess.CalledProcessError, NotImplementedError) as e:
        raise InstallationError(f"Failed to install {program}") from e


async def generate_encryption_phrase(persona: Persona) -> str:
    """Generate a recovery phrase for the persona."""
    logger.info("Generating encryption phrase", {"persona_id": persona.id})
    return await local_model.generate_encryption_phrase(persona)


async def save_phrases(persona: Persona, phrase: str) -> None:
    """Save the encryption phrase in OS secure storage."""
    logger.info("Saving encryption phrase", {"persona_id": persona.id})
    platform = OS.get_supported()

    if platform is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")

    try:
        if platform == "linux":
            await linux.store_secret(persona.id, phrase)
        elif platform == "mac":
            await mac.store_secret(persona.id, phrase)
        elif platform == "windows":
            await windows.store_secret(persona.id, phrase)
    except Exception as e:
        raise SecretStorageError("Failed to save encryption phrase to secure storage") from e


async def get_phrases(persona: Persona) -> str:
    """Retrieve the encryption phrase from OS secure storage."""
    logger.info("Retrieving encryption phrase", {"persona_id": persona.id})
    platform = OS.get_supported()

    if platform is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")

    try:
        if platform == "linux":
            return await linux.retrieve_secret(persona.id)
        elif platform == "mac":
            return await mac.retrieve_secret(persona.id)
        elif platform == "windows":
            return await windows.retrieve_secret(persona.id)
    except Exception as e:
        raise SecretStorageError("Failed to retrieve encryption phrase from secure storage") from e
