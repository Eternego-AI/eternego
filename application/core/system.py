"""System — generic program availability and installation."""

import subprocess

from application.platform import logger, crypto, OS, bip39
from application.core.data import Persona
from application.core.exceptions import UnsupportedOS, InstallationError, SecretStorageError, ExecutionError, HardwareError


async def execute(tool_calls: list[dict]) -> str:
    """Execute approved tool calls and return combined results."""
    logger.info("Executing tool calls", {"count": len(tool_calls)})
    if OS.get_supported() is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")

    results = []
    for call in tool_calls:
        func = call.get("function", {})
        name = func.get("name", "")
        args = func.get("arguments", {})
        command = args.get("command", "")
        logger.info("Running tool", {"name": name, "command": command})

        code, output = await OS.execute(command)

        if code != 0:
            raise ExecutionError(f"{name}: {output}")

        results.append(f"{name}: {output}")
    return "\n".join(results)


def make_rows_traceable(rows: list[str], prefix: str) -> list[dict]:
    """Tag each row with a trackable ID using its content hash."""
    return [
        {"id": f"{prefix}-{crypto.generate_unique_id(row)}", "content": row}
        for row in rows
    ]


async def is_installed(program: str) -> bool:
    """Check if a program is installed on the current OS."""
    logger.info("Checking if program is installed", {"program": program})
    if OS.get_supported() is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")
    return await OS.is_installed(program)


async def install(program: str) -> None:
    """Install a program on the current OS."""
    logger.info("Installing program", {"program": program})
    if OS.get_supported() is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")
    try:
        await OS.install(program)
    except (subprocess.CalledProcessError, NotImplementedError) as e:
        raise InstallationError(f"Failed to install {program}") from e


async def save_phrases(persona: Persona, phrase: str) -> None:
    """Save the encryption phrase in OS secure storage."""
    logger.info("Saving encryption phrase", {"persona_id": persona.id})
    if OS.get_supported() is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")
    try:
        await OS.store_secret(persona.id, phrase)
    except Exception as e:
        raise SecretStorageError("Failed to save encryption phrase to secure storage") from e


async def get_phrases(persona: Persona) -> str:
    """Retrieve the encryption phrase from OS secure storage."""
    logger.info("Retrieving encryption phrase", {"persona_id": persona.id})
    if OS.get_supported() is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")
    try:
        return await OS.retrieve_secret(persona.id)
    except Exception as e:
        raise SecretStorageError("Failed to retrieve encryption phrase from secure storage") from e


def hardware() -> dict:
    """Return current hardware information."""
    logger.info("Reading hardware info")
    try:
        return {
            "ram_gb": OS.ram_gb(),
            "gpu_vram_gb": OS.gpu_vram_gb(),
            "cpu": OS.cpu_name(),
            "os": OS.os_name(),
        }
    except (OSError, subprocess.CalledProcessError, RuntimeError) as e:
        raise HardwareError("Could not read hardware information") from e


def generate_recovery_phrases() -> str:
    """Generate a cryptographically secure recovery phrase."""
    logger.info("Generating recovery phrase")
    return bip39.choose(24)


async def persona_key(phrase: str, persona_id: str) -> bytes:
    """Derive a symmetric encryption key for the persona from the phrase."""
    logger.info("Deriving persona key", {"persona_id": persona_id})
    return crypto.derive_key(phrase, persona_id.encode())
