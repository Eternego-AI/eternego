"""Person — the human behind the persona."""

from application.platform import logger, filesystem
from application.core.data import Persona
from application.core.exceptions import PersonError


async def prepare_buckets(persona: Persona) -> None:
    """Prepare the person's identity and traits files."""
    logger.info("Preparing person buckets", {"persona_id": persona.id})
    try:
        filesystem.write(persona.storage_dir / "person-identity.md", "")
        filesystem.write(persona.storage_dir / "person-traits.md", "")
    except OSError as e:
        raise PersonError("Failed to prepare person buckets") from e


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
