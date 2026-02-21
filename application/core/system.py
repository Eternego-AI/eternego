"""System — generic program availability and installation."""

import json as _json
import subprocess

from application.platform import logger, crypto, OS, linux, mac, windows
from application.core import local_model
from application.core.data import Persona
from application.core.exceptions import UnsupportedOS, InstallationError, SecretStorageError, ExecutionError


async def execute(tool_calls: list[dict]) -> str:
    """Execute approved tool calls and return combined results."""
    logger.info("Executing tool calls", {"count": len(tool_calls)})
    platform = OS.get_supported()

    if platform is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")

    results = []
    for call in tool_calls:
        func = call.get("function", {})
        name = func.get("name", "")
        args = func.get("arguments", {})
        command = args.get("command", "")
        logger.info("Running tool", {"name": name, "command": command})

        if platform == "linux":
            code, output = await linux.execute_on_sub_process(command)
        elif platform == "mac":
            code, output = await mac.execute_on_sub_process(command)
        elif platform == "windows":
            code, output = await windows.execute_on_sub_process(command)

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


async def get_pairing_codes() -> dict[str, dict]:
    """Return all pending pairing codes from OS secure storage. Each entry has persona, channel, created_at."""
    logger.info("Retrieving pairing codes")
    platform = OS.get_supported()
    if platform is None:
        return {}
    try:
        if platform == "linux":
            raw = await linux.retrieve_secret("pairing_codes")
        elif platform == "mac":
            raw = await mac.retrieve_secret("pairing_codes")
        elif platform == "windows":
            raw = await windows.retrieve_secret("pairing_codes")
        else:
            return {}
        from datetime import datetime
        from application.core import agent as _agent
        from application.core.data import Channel
        result = {}
        for code, entry in _json.loads(raw).items():
            try:
                persona = _agent.find(entry["persona_id"])
                channel = Channel(**entry["channel"])
                created_at = datetime.fromisoformat(entry["created_at"])
                result[code] = {"persona": persona, "channel": channel, "created_at": created_at}
            except Exception:
                continue
        return result
    except Exception:
        return {}


async def save_pairing_code(code: str, persona, channel) -> None:
    """Store a pairing code with its persona and channel in OS secure storage."""
    logger.info("Saving pairing code", {"code": code, "persona_id": persona.id})
    platform = OS.get_supported()
    if platform is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")
    try:
        from application.platform import datetimes, objects
        existing = {}
        try:
            if platform == "linux":
                raw = await linux.retrieve_secret("pairing_codes")
            elif platform == "mac":
                raw = await mac.retrieve_secret("pairing_codes")
            elif platform == "windows":
                raw = await windows.retrieve_secret("pairing_codes")
            existing = _json.loads(raw)
        except Exception:
            pass
        existing[code] = {
            "persona_id": persona.id,
            "channel": objects.json(channel),
            "created_at": datetimes.iso_8601(datetimes.now()),
        }
        serialized = _json.dumps(existing)
        if platform == "linux":
            await linux.store_secret("pairing_codes", serialized)
        elif platform == "mac":
            await mac.store_secret("pairing_codes", serialized)
        elif platform == "windows":
            await windows.store_secret("pairing_codes", serialized)
    except (UnsupportedOS, SecretStorageError):
        raise
    except Exception as e:
        raise SecretStorageError("Failed to save pairing code to secure storage") from e


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
