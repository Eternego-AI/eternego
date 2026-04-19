"""Persona — controlling what a persona knows."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Persona
from application.core.exceptions import IdentityError, PersonError


@dataclass
class ControlData:
    removed: int


async def control(persona: Persona, entry_ids: list[str]) -> Outcome[ControlData]:
    """It gives you full control over what your persona knows — you always have the final say."""
    bus.propose("Controlling persona", {"persona": persona, "count": len(entry_ids)})

    try:
        for entry_id in entry_ids:
            prefix, hash_part = entry_id.split("-", 1)

            if prefix == "pi":
                paths.delete_entry(paths.person_identity(persona.id), hash_part)
            elif prefix == "pt":
                paths.delete_entry(paths.person_traits(persona.id), hash_part)
            elif prefix == "pc":
                paths.delete_entry(paths.persona_trait(persona.id), hash_part)
            elif prefix == "hist":
                paths.find_and_delete_file(paths.history(persona.id), hash_part)
            elif prefix == "dest":
                paths.find_and_delete_file(paths.destiny(persona.id), hash_part)
            elif prefix == "wi":
                paths.delete_entry(paths.wishes(persona.id), hash_part)
            elif prefix == "ps":
                paths.delete_entry(paths.struggles(persona.id), hash_part)

        bus.broadcast("Persona controlled", {"persona": persona, "removed": len(entry_ids)})

        return Outcome(
            success=True,
            message="Entries removed successfully",
            data=ControlData(removed=len(entry_ids)),
        )

    except ValueError:
        bus.broadcast("Persona control failed", {"reason": "invalid_id", "persona": persona})
        return Outcome(success=False, message="Invalid entry ID format.")

    except IdentityError as e:
        bus.broadcast("Persona control failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not remove agent entry. It may have been modified or already deleted.")

    except PersonError as e:
        bus.broadcast("Persona control failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not remove person entry. It may have been modified or already deleted.")
