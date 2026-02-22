"""Agent — persona identity initialization and management."""

import json
from datetime import date

from application.platform import logger, filesystem, datetimes, objects
from application.core import paths, prompts
from application.core.data import Channel, Model, Persona
from application.core.exceptions import IdentityError



async def refine_context(persona: Persona, new_items: list[str]) -> None:
    """Consolidate new context notes with existing ones using the local model."""
    logger.info("Refining context", {"persona_id": persona.id})
    try:
        from application.core import local_model, prompts
        path = persona.storage_dir / "persona-context.md"
        existing = filesystem.read(path).strip() if path.exists() else ""
        refined = await local_model.respond(
            persona.model.name,
            [{"role": "user", "content": prompts.context_refinement(existing, new_items)}],
        )
        filesystem.write(path, refined.strip() + "\n" if refined.strip() else "")
    except OSError as e:
        raise IdentityError("Failed to refine context") from e


def find(persona_id: str) -> Persona:
    """Load the persona for the given persona_id from its identity file."""
    logger.info("Loading persona", {"persona_id": persona_id})
    config_path = paths.persona_identity(persona_id)
    try:
        if not config_path.exists():
            raise IdentityError("Persona not found")
        config = filesystem.read_json(config_path)
        return Persona(
            id=config["id"],
            name=config["name"],
            model=Model(**config["model"]),
            version=config.get("version", "v1"),
            base_model=config.get("base_model", config["model"]["name"]),
            birthday=config.get("birthday", str(date.today())),
            frontier=Model(**config["frontier"]) if config.get("frontier") else None,
            channels=[Channel(**n) for n in config["channels"]] if config.get("channels") else None,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise IdentityError("Persona data is malformed") from e
    except OSError as e:
        raise IdentityError("Failed to load persona") from e
