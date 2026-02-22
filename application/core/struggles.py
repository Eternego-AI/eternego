"""Struggles — the person's recurring obstacles as observed by the persona."""

from application.platform import logger, filesystem, crypto
from application.core import paths
from application.core.data import Persona
from application.core.exceptions import PersonError


async def identify(persona: Persona, observed: list[str]) -> None:
    """Append newly observed struggles to the person's struggles file."""
    logger.info("Identifying struggles", {"persona_id": persona.id})
    try:
        if observed:
            filesystem.append(await paths.struggles(persona.id), "\n".join(observed) + "\n")
    except OSError as e:
        raise PersonError("Failed to save struggles") from e


async def refine(persona: Persona, new_items: list[str]) -> None:
    """Consolidate new struggles with existing ones using the local model."""
    logger.info("Refining struggles", {"persona_id": persona.id})
    try:
        from application.core import local_model, prompts
        path = await paths.struggles(persona.id)
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
        path = await paths.struggles(persona.id)
        return filesystem.read(path).strip() if path.exists() else ""
    except OSError as e:
        raise PersonError("Failed to read struggles") from e


