"""DNA — compressed synthesis of everything the persona knows about the person."""

from application.platform import logger, filesystem
from application.core.data import Persona
from application.core.exceptions import DNAError


async def make(persona: Persona) -> None:
    """Create an empty DNA file for a new persona."""
    logger.info("Creating DNA file", {"persona_id": persona.id})
    try:
        filesystem.write(persona.storage_dir / "dna.md", "")
    except OSError as e:
        raise DNAError("Failed to create DNA file") from e


def read(persona: Persona) -> str:
    """Read the persona's DNA file."""
    logger.info("Reading DNA", {"persona_id": persona.id})
    try:
        path = persona.storage_dir / "dna.md"
        if not path.exists():
            raise DNAError("DNA file not found")
        return filesystem.read(path)
    except OSError as e:
        raise DNAError("Failed to read DNA file") from e


async def evolve(persona: Persona, content: str) -> None:
    """Overwrite the DNA file with new synthesis."""
    logger.info("Evolving DNA", {"persona_id": persona.id})
    try:
        filesystem.write(persona.storage_dir / "dna.md", content)
    except OSError as e:
        raise DNAError("Failed to save DNA file") from e


