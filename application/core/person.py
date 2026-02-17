"""Person — the human behind the persona."""

from application.platform import logger, filesystem, crypto
from application.core.data import Persona
from application.core.exceptions import PersonError


async def bond(persona: Persona) -> None:
    """Connect the person to the persona — prepare identity and traits files."""
    logger.info("Bonding person to persona", {"persona_id": persona.id})
    try:
        filesystem.write(persona.storage_dir / "person-identity.md", "")
        filesystem.write(persona.storage_dir / "person-traits.md", "")
    except OSError as e:
        raise PersonError("Failed to prepare person buckets") from e


async def identified_by(persona: Persona) -> list[str]:
    """Read how the person is identified by this persona."""
    logger.info("Reading person identity", {"persona_id": persona.id})
    try:
        content = filesystem.read(persona.storage_dir / "person-identity.md")
        return [line for line in content.splitlines() if line.strip()]
    except OSError as e:
        raise PersonError("Failed to read person identity") from e


async def traits_toward(persona: Persona) -> list[str]:
    """Read the person's behavioral traits toward this persona."""
    logger.info("Reading person traits", {"persona_id": persona.id})
    try:
        content = filesystem.read(persona.storage_dir / "person-traits.md")
        return [line for line in content.splitlines() if line.strip()]
    except OSError as e:
        raise PersonError("Failed to read person traits") from e


async def delete_identity(persona: Persona, hash_part: str) -> None:
    """Remove a fact from person identity by its content hash."""
    logger.info("Deleting identity entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        path = persona.storage_dir / "person-identity.md"
        content = filesystem.read(path)
        lines = content.splitlines()
        remaining = [line for line in lines if crypto.generate_unique_id(line) != hash_part]
        if len(remaining) == len(lines):
            raise PersonError("Entry not found or already modified")
        filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")
    except OSError as e:
        raise PersonError("Failed to delete identity entry") from e


async def delete_trait(persona: Persona, hash_part: str) -> None:
    """Remove a trait from person traits by its content hash."""
    logger.info("Deleting trait entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        path = persona.storage_dir / "person-traits.md"
        content = filesystem.read(path)
        lines = content.splitlines()
        remaining = [line for line in lines if crypto.generate_unique_id(line) != hash_part]
        if len(remaining) == len(lines):
            raise PersonError("Entry not found or already modified")
        filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")
    except OSError as e:
        raise PersonError("Failed to delete trait entry") from e



async def add_facts(persona: Persona, facts: list[str]) -> None:
    """Save factual observations about the person."""
    logger.info("Adding facts", {"persona_id": persona.id})
    try:
        if facts:
            filesystem.append(persona.storage_dir / "person-identity.md", "\n".join(facts) + "\n")
    except OSError as e:
        raise PersonError("Failed to save facts") from e


async def add_traits(persona: Persona, traits: list[str]) -> None:
    """Save behavioral traits observed about the person."""
    logger.info("Adding traits", {"persona_id": persona.id})
    try:
        if traits:
            filesystem.append(persona.storage_dir / "person-traits.md", "\n".join(traits) + "\n")
    except OSError as e:
        raise PersonError("Failed to save traits") from e
