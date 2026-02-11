"""Agent — persona identity initialization and management."""

import json
import uuid
from dataclasses import asdict
from pathlib import Path

from application.platform import logger, filesystem, crypto
from application.core import prompts
from application.core.data import Channel, Model, Persona
from application.core.exceptions import IdentityError


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


async def prepare_buckets(persona: Persona) -> None:
    """Prepare the agent's identity, context, and training buckets."""
    logger.info("Preparing agent buckets", {"persona_id": persona.id})
    try:
        filesystem.write(persona.storage_dir / "persona-identity.md", "")
        filesystem.write(persona.storage_dir / "persona-context.md", "")
        filesystem.ensure_dir(persona.storage_dir / "training")
        filesystem.ensure_dir(persona.storage_dir / "memory")
    except OSError as e:
        raise IdentityError("Failed to prepare agent buckets") from e


async def give_instructions(persona: Persona) -> None:
    """Load instructions into a persona."""
    logger.info("Giving instructions", {"persona_id": persona.id})
    try:
        path = persona.storage_dir / "instructions"
        for key, content in prompts.BASIC_INSTRUCTIONS.items():
            filesystem.write(path / f"{key}.md", content)
    except OSError as e:
        raise IdentityError("Failed to give instructions") from e


async def add_instruction(persona: Persona, name: str, content: str) -> None:
    """Add a single instruction to a persona."""
    logger.info("Adding instruction", {"persona_id": persona.id, "name": name})
    try:
        path = persona.storage_dir / "instructions"
        filesystem.write(path / f"{name}.md", content)
    except OSError as e:
        raise IdentityError("Failed to add instruction") from e


async def equip_basic_skills(persona: Persona) -> None:
    """Prepare the skills directory for a persona."""
    logger.info("Equipping basic skills", {"persona_id": persona.id})
    try:
        filesystem.ensure_dir(persona.storage_dir / "skills")
    except OSError as e:
        raise IdentityError("Failed to equip basic skills") from e


async def identity(persona: Persona) -> dict[str, list[str]]:
    """Read the agent's identity and context."""
    logger.info("Reading agent identity", {"persona_id": persona.id})
    try:
        identity_content = filesystem.read(persona.storage_dir / "persona-identity.md")
        context_content = filesystem.read(persona.storage_dir / "persona-context.md")

        return {
            "identity": [line for line in identity_content.splitlines() if line.strip()],
            "context": [line for line in context_content.splitlines() if line.strip()],
        }
    except OSError as e:
        raise IdentityError("Failed to read agent identity") from e


async def skills(persona: Persona) -> list[str]:
    """Read the agent's skill names."""
    logger.info("Reading agent skills", {"persona_id": persona.id})
    try:
        names = []
        skills_dir = persona.storage_dir / "skills"
        if skills_dir.exists():
            for file in sorted(skills_dir.glob("*.md")):
                names.append(file.stem)
        return names
    except OSError as e:
        raise IdentityError("Failed to read agent skills") from e


async def memory(persona: Persona) -> list[str]:
    """Read the agent's conversation names since last sleep."""
    logger.info("Reading agent memory", {"persona_id": persona.id})
    try:
        names = []
        memory_dir = persona.storage_dir / "memory"
        if memory_dir.exists():
            for file in sorted(memory_dir.glob("*")):
                names.append(file.stem)
        return names
    except OSError as e:
        raise IdentityError("Failed to read agent memory") from e


async def delete_identity(persona: Persona, hash_part: str) -> None:
    """Remove an entry from persona identity by its content hash."""
    logger.info("Deleting identity entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        path = persona.storage_dir / "persona-identity.md"
        content = filesystem.read(path)
        lines = content.splitlines()
        remaining = [line for line in lines if crypto.generate_unique_id(line) != hash_part]
        if len(remaining) == len(lines):
            raise IdentityError("Entry not found or already modified")
        filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")
    except OSError as e:
        raise IdentityError("Failed to delete identity entry") from e


async def delete_context(persona: Persona, hash_part: str) -> None:
    """Remove an entry from persona context by its content hash."""
    logger.info("Deleting context entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        path = persona.storage_dir / "persona-context.md"
        content = filesystem.read(path)
        lines = content.splitlines()
        remaining = [line for line in lines if crypto.generate_unique_id(line) != hash_part]
        if len(remaining) == len(lines):
            raise IdentityError("Entry not found or already modified")
        filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")
    except OSError as e:
        raise IdentityError("Failed to delete context entry") from e


async def delete_skill(persona: Persona, hash_part: str) -> None:
    """Remove a skill file by its name hash."""
    logger.info("Deleting skill", {"persona_id": persona.id, "hash": hash_part})
    try:
        skills_dir = persona.storage_dir / "skills"
        for file in skills_dir.glob("*.md"):
            if crypto.generate_unique_id(file.stem) == hash_part:
                filesystem.delete(file)
                return
        raise IdentityError("Skill not found or already removed")
    except OSError as e:
        raise IdentityError("Failed to delete skill") from e


async def delete_memory(persona: Persona, hash_part: str) -> None:
    """Remove a conversation file by its name hash."""
    logger.info("Deleting memory", {"persona_id": persona.id, "hash": hash_part})
    try:
        memory_dir = persona.storage_dir / "memory"
        for file in memory_dir.glob("*"):
            if crypto.generate_unique_id(file.stem) == hash_part:
                filesystem.delete(file)
                return
        raise IdentityError("Memory entry not found or already removed")
    except OSError as e:
        raise IdentityError("Failed to delete memory entry") from e


async def learn(persona: Persona, context: list[str]) -> None:
    """Save context observations to the persona's context file."""
    logger.info("Learning from context", {"persona_id": persona.id})
    try:
        if context:
            filesystem.append(persona.storage_dir / "persona-context.md", "\n".join(context) + "\n")
    except OSError as e:
        raise IdentityError("Failed to save context") from e


async def distill(materials: Path) -> Persona:
    """Restore a persona from diary materials into the personas directory."""
    logger.info("Distilling persona from materials", {"path": str(materials)})
    try:
        config = filesystem.read_json(materials / "config.json")
        persona = Persona(
            id=config["id"],
            name=config["name"],
            model=Model(**config["model"]),
            frontier=Model(**config["frontier"]) if config.get("frontier") else None,
            channels=[Channel(**ch) for ch in config["channels"]] if config.get("channels") else None,
        )
        filesystem.copy_dir(materials, persona.storage_dir)
        return persona
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise IdentityError("Persona data is malformed") from e
    except OSError as e:
        raise IdentityError("Failed to restore persona files") from e


async def save_persona(persona: Persona) -> None:
    """Save persona configuration."""
    logger.info("Saving persona", {"persona_id": persona.id})
    try:
        filesystem.write_json(persona.storage_dir / "config.json", asdict(persona))
    except OSError as e:
        raise IdentityError("Failed to save persona") from e
