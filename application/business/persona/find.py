"""Persona — finding a persona by ID."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Channel, Model, Persona
from application.core.exceptions import IdentityError


@dataclass
class FindData:
    persona: Persona


async def find(persona_id: str) -> Outcome[FindData]:
    """Find a persona by its ID."""
    await bus.propose("Finding persona", {"persona_id": persona_id})
    try:
        identity_path = paths.persona_identity(persona_id)
        if not identity_path.exists():
            await bus.broadcast("Persona not found", {"persona_id": persona_id})
            return Outcome(success=False, message="Persona not found.")

        raw_persona = paths.read_json(identity_path)
        thinking_data = raw_persona["thinking"]
        persona = Persona(
            id=raw_persona["id"],
            name=raw_persona["name"],
            thinking=Model(**thinking_data),
            version=raw_persona.get("version"),
            base_model=raw_persona.get("base_model", thinking_data["name"]),
            birthday=raw_persona.get("birthday"),
            frontier=Model(**raw_persona["frontier"]) if raw_persona.get("frontier") else None,
            channels=[Channel(**n) for n in raw_persona["channels"]] if raw_persona.get("channels") else None,
        )

        await bus.broadcast("Persona found", {"persona": persona})
        return Outcome(success=True, message="", data=FindData(persona=persona))
    except IdentityError as e:
        await bus.broadcast("Persona not found", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message="Persona not found.")
