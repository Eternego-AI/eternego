"""Skills — knowledge and procedural documents for a persona."""

from pathlib import Path

from application.platform import logger, filesystem, crypto
from application.core import local_model
from application.core.data import Observation, Persona
from application.core.exceptions import IdentityError, SkillError


_DEFAULTS_DIR = Path(__file__).parent / "default_skills"


async def equip(persona: Persona) -> None:
    """Prepare the skills directory and install default skills with observations."""
    logger.info("Equipping skills", {"persona_id": persona.id})
    from application.core import observations
    try:
        filesystem.ensure_dir(persona.storage_dir / "skills")
        workspace = str(persona.storage_dir / "workspace")
        for source in sorted(_DEFAULTS_DIR.glob("*.md")):
            content = filesystem.read(source).replace("{workspace}", workspace)
            filesystem.write(persona.storage_dir / "skills" / source.name, content)
    except OSError as e:
        raise IdentityError("Failed to equip skills") from e
    try:
        for skill_file in sorted((persona.storage_dir / "skills").glob("*.md")):
            observed = await summarize(persona, skill_file)
            await observations.effect(persona, observed)
    except Exception as e:
        logger.error("Failed to assess default skills", {"persona_id": persona.id, "error": str(e)})
        raise SkillError("Failed to assess default skills") from e


async def shelve(persona: Persona, skill_path: str) -> Path:
    """Read a skill document and save it to the persona's skills directory."""
    logger.info("Shelving skill", {"persona_id": persona.id, "path": skill_path})
    try:
        source = Path(skill_path)
        content = filesystem.read(source)
        destination = persona.storage_dir / "skills" / source.name
        if destination.exists():
            raise IdentityError(f"Skill '{source.stem}' already exists")
        filesystem.write(destination, content)
        return destination
    except OSError as e:
        raise IdentityError("Failed to shelve skill") from e


async def summarize(persona: Persona, skill_path: Path) -> Observation:
    """Read a skill and assess what it means for person and persona."""
    logger.info("Summarizing skill", {"persona_id": persona.id, "skill": skill_path.stem})
    try:
        content = filesystem.read(skill_path)
        return await local_model.assess_skill(persona.model.name, skill_path.stem, content)
    except OSError as e:
        raise IdentityError("Failed to read skill for summarization") from e


async def names(persona: Persona) -> list[str]:
    """Read the agent's skill names."""
    logger.info("Reading skill names", {"persona_id": persona.id})
    try:
        result = []
        skills_dir = persona.storage_dir / "skills"
        if skills_dir.exists():
            for file in sorted(skills_dir.glob("*.md")):
                result.append(file.stem)
        return result
    except OSError as e:
        raise IdentityError("Failed to read skill names") from e


async def delete(persona: Persona, hash_part: str) -> None:
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
