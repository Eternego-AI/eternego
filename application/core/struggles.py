"""Struggles — the person's recurring obstacles as observed by the persona."""

from application.platform import logger, filesystem, crypto
from application.core import paths
from application.core.data import Persona
from application.core.exceptions import PersonError


async def be_mindful(persona: Persona) -> None:
    """Create an empty struggles file for a new persona."""
    logger.info("Preparing struggles file", {"persona_id": persona.id})
    try:
        filesystem.write(paths.struggles(persona.id), "")
    except OSError as e:
        raise PersonError("Failed to prepare struggles file") from e


async def identify(persona: Persona, observed: list[str]) -> None:
    """Append newly observed struggles to the person's struggles file."""
    logger.info("Identifying struggles", {"persona_id": persona.id})
    try:
        if observed:
            filesystem.append(paths.struggles(persona.id), "\n".join(observed) + "\n")
    except OSError as e:
        raise PersonError("Failed to save struggles") from e


async def refine(persona: Persona, new_items: list[str]) -> None:
    """Consolidate new struggles with existing ones using the local model."""
    logger.info("Refining struggles", {"persona_id": persona.id})
    try:
        from application.core import local_model, prompts
        path = paths.struggles(persona.id)
        existing = filesystem.read(path).strip() if path.exists() else ""
        refined = await local_model.respond(
            persona.model.name,
            [{"role": "user", "content": prompts.struggle_refinement(existing, new_items)}],
        )
        filesystem.write(path, refined.strip() + "\n" if refined.strip() else "")
    except OSError as e:
        raise PersonError("Failed to refine struggles") from e


async def identified_by(persona: Persona) -> str:
    """Read the person's known struggles."""
    logger.info("Reading struggles", {"persona_id": persona.id})
    try:
        path = paths.struggles(persona.id)
        return filesystem.read(path).strip() if path.exists() else ""
    except OSError as e:
        raise PersonError("Failed to read struggles") from e


async def as_list(persona: Persona) -> list[str]:
    """Return the person's known struggles as a list of lines."""
    logger.info("Listing struggles", {"persona_id": persona.id})
    try:
        path = paths.struggles(persona.id)
        content = filesystem.read(path) if path.exists() else ""
        return [line for line in content.splitlines() if line.strip()]
    except OSError as e:
        raise PersonError("Failed to read struggles") from e


async def delete(persona: Persona, hash_part: str) -> None:
    """Remove a struggle entry by its content hash."""
    logger.info("Deleting struggle entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        path = paths.struggles(persona.id)
        content = filesystem.read(path)
        lines = content.splitlines()
        remaining = [line for line in lines if crypto.generate_unique_id(line) != hash_part]
        if len(remaining) == len(lines):
            raise PersonError("Entry not found or already modified")
        filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")
    except OSError as e:
        raise PersonError("Failed to delete struggle entry") from e
