"""Instructions — operating instructions for a persona."""

from application.platform import logger, filesystem
from application.core import prompts
from application.core.data import Persona
from application.core.exceptions import IdentityError


def read(persona: Persona) -> str:
    """Read and join all instruction files for a persona."""
    instructions_dir = persona.storage_dir / "instructions"
    if not instructions_dir.exists():
        return ""
    parts = []
    for file in sorted(instructions_dir.glob("*.md")):
        parts.append(filesystem.read(file))
    return "\n\n".join(parts)


async def give(persona: Persona) -> None:
    """Load foundational instructions into a persona."""
    logger.info("Giving instructions", {"persona_id": persona.id})
    try:
        path = persona.storage_dir / "instructions"
        for key, content in prompts.BASIC_INSTRUCTIONS.items():
            filesystem.write(path / f"{key}.md", content)
    except OSError as e:
        raise IdentityError("Failed to prepare instructions") from e


async def add(persona: Persona, name: str, content: str) -> None:
    """Add a single instruction to a persona."""
    logger.info("Adding instruction", {"persona_id": persona.id, "name": name})
    try:
        path = persona.storage_dir / "instructions"
        filesystem.write(path / f"{name}.md", content)
    except OSError as e:
        raise IdentityError("Failed to add instruction") from e
