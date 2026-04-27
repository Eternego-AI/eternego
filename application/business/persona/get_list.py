"""Persona — listing all personas."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Persona
from application.core.exceptions import IdentityError

from .find import find


@dataclass
class GetListData:
    personas: list[Persona]


async def get_list() -> Outcome[GetListData]:
    """Return all personas."""
    bus.propose("Listing personas", {})

    try:
        root = paths.personas_home()
        if not root.exists():
            bus.broadcast("No personas found", {})
            return Outcome(success=False, message="No personas found. Create one to get started.", data=GetListData(personas=[]))
        try:
            persona_ids = [d.name for d in root.iterdir() if d.is_dir() and (d / "home" / "config.json").exists()]
        except OSError as e:
            raise IdentityError("Failed to list personas") from e
        personas = []
        for persona_id in persona_ids:
            try:
                outcome = await find(persona_id)
                if outcome.success:
                    personas.append(outcome.data.persona)
            except (IdentityError, OSError):
                continue

        bus.broadcast("Personas list", {"personas": personas})
        return Outcome(success=True, message="", data=GetListData(personas=personas))
    except IdentityError as e:
        bus.broadcast("List personas failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not list personas. Please check the persona data.")
