"""Persona — deleting a persona and its data."""

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine, models, paths
from application.core.data import Persona
from application.core.exceptions import EngineConnectionError, IdentityError


async def delete(persona: Persona) -> Outcome[dict]:
    """Delete a persona and all its data."""
    await bus.propose("Deleting persona", {"persona": persona})
    try:
        paths.delete_recursively(paths.home(persona.id))
        if models.is_local(persona.thinking):
            await local_inference_engine.delete(persona.thinking.url, persona.thinking.name)
        await bus.broadcast("Persona deleted", {"persona": persona})
        return Outcome(success=True, message="Persona deleted successfully")
    except IdentityError as e:
        await bus.broadcast("Persona deletion failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not delete persona. Please check the persona data.")
    except EngineConnectionError as e:
        await bus.broadcast("Persona deletion failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine to delete the model. Please make sure it is running.")
