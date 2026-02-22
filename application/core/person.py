"""Person — the human behind the persona."""
from application.core import paths
from application.platform import logger, filesystem, crypto
from application.core.data import Persona
from application.core.exceptions import PersonError


async def add_facts(persona: Persona, facts: list[str]) -> None:
    """Save factual observations about the person."""
    logger.info("Adding facts", {"persona_id": persona.id})
    try:
        if facts:
            await paths.add_person_identity(persona.id, "".join(facts) + "\n")
    except OSError as e:
        raise PersonError("Failed to save facts") from e


async def add_traits(persona: Persona, traits: list[str]) -> None:
    """Save behavioral traits observed about the person."""
    logger.info("Adding traits", {"persona_id": persona.id})
    try:
        if traits:
            await paths.add_person_traits(persona.id, "".join(traits) + "\n")
    except OSError as e:
        raise PersonError("Failed to save traits") from e


async def add_struggles(persona: Persona, struggles: list[str]) -> None:
    """Save struggles observed about the person."""
    logger.info("Adding struggles", {"persona_id": persona.id})
    try:
        if struggles:
            await paths.add_struggles(persona.id, "".join(struggles) + "\n")
    except OSError as e:
        raise PersonError("Failed to save struggles") from e


async def refine_traits(persona: Persona, new_items: list[str]) -> None:
    """Consolidate new traits with existing ones using the local model."""
    logger.info("Refining traits", {"persona_id": persona.id})
    try:
        from application.core import local_model, prompts
        path = persona.storage_dir / "person-traits.md"
        existing = filesystem.read(path).strip() if path.exists() else ""
        refined = await local_model.respond(
            persona.model.name,
            [{"role": "user", "content": prompts.trait_refinement(existing, new_items)}],
        )
        filesystem.write(path, refined.strip() + "\n" if refined.strip() else "")
    except OSError as e:
        raise PersonError("Failed to refine traits") from e
