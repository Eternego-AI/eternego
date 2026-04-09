"""Persona — listing all personas."""

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.exceptions import IdentityError

from .find import find


async def get_list() -> Outcome[dict]:
    """Return all personas."""
    await bus.propose("Listing personas", {})

    try:
        root = paths.personas_home()
        if not root.exists():
            await bus.broadcast("No personas found", {})
            return Outcome(success=False, message="No personas found. Create one to get started.", data={"personas": []})
        try:
            persona_ids = [d.name for d in root.iterdir() if d.is_dir() and (d / "home" / "config.json").exists()]
        except OSError as e:
            raise IdentityError("Failed to list personas") from e
        personas = []
        for persona_id in persona_ids:
            try:
                outcome = await find(persona_id)
                if outcome.success:
                    personas.append(outcome.data["persona"])
            except (IdentityError, OSError):
                continue

        await bus.broadcast("Personas listed", {"count": len(personas)})
        return Outcome(success=True, message="", data={"personas": personas})
    except IdentityError as e:
        await bus.broadcast("List personas failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not list personas. Please check the persona data.")
