"""Identity — persona identity initialization and management."""

import uuid
from dataclasses import asdict
from pathlib import Path

from application.platform import logger, filesystem, OS, linux, mac, windows
from application.core.data import Channel, Model, Persona
from application.core.exceptions import UnsupportedOS, SecretStorageError


PERSONAS_DIR = Path.home() / ".eternego" / "personas"


def memory_path(persona: Persona) -> Path:
    """Return the persona's directory path."""
    return PERSONAS_DIR / persona.id


async def initialize(
    name: str,
    model: Model,
    frontier: Model | None = None,
    channels: list[Channel] | None = None,
) -> Persona:
    """Create a new persona with a fresh identity."""
    logger.info("Initializing persona identity", {"name": name, "model": model.name})
    persona_id = str(uuid.uuid4())
    return Persona(
        id=persona_id,
        name=name,
        model=model,
        frontier=frontier,
        channels=channels,
    )


async def prepare_person_identity_bucket(persona: Persona) -> None:
    """Prepare the person identity file."""
    logger.info("Preparing person identity bucket", {"persona_id": persona.id})
    filesystem.write(PERSONAS_DIR / persona.id / "person-identity.md", "")


async def prepare_person_traits_bucket(persona: Persona) -> None:
    """Prepare the person traits file."""
    logger.info("Preparing person traits bucket", {"persona_id": persona.id})
    filesystem.write(PERSONAS_DIR / persona.id / "person-traits.md", "")


async def prepare_persona_identity_bucket(persona: Persona) -> None:
    """Prepare the persona identity file."""
    logger.info("Preparing persona identity bucket", {"persona_id": persona.id})
    filesystem.write(PERSONAS_DIR / persona.id / "persona-identity.md", "")


async def prepare_persona_context_bucket(persona: Persona) -> None:
    """Prepare the persona context file."""
    logger.info("Preparing persona context bucket", {"persona_id": persona.id})
    filesystem.write(PERSONAS_DIR / persona.id / "persona-context.md", "")


async def prepare_training_material_bucket(persona: Persona) -> None:
    """Prepare the training material storage."""
    logger.info("Preparing training material bucket", {"persona_id": persona.id})
    path = PERSONAS_DIR / persona.id / "training"
    filesystem.ensure_dir(path)


async def instructions(persona: Persona, data: dict[str, str]) -> None:
    """Load instructions into a persona."""
    logger.info("Loading instructions", {"persona_id": persona.id})
    path = PERSONAS_DIR / persona.id / "instructions"
    for key, content in data.items():
        filesystem.write(path / f"{key}.md", content)


async def skills(persona: Persona, data: dict[str, str]) -> None:
    """Load skills into a persona."""
    logger.info("Loading skills", {"persona_id": persona.id})
    path = PERSONAS_DIR / persona.id / "skills"
    for key, content in data.items():
        filesystem.write(path / f"{key}.md", content)


async def save_persona(persona: Persona) -> None:
    """Save persona configuration."""
    logger.info("Saving persona", {"persona_id": persona.id})
    path = memory_path(persona) / "config.json"
    filesystem.write_json(path, asdict(persona))


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
