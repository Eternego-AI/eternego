"""Persona — getting a loaded persona from the registry."""

from application.business.outcome import Outcome
from application.core import agents, bus
from application.core.exceptions import MindError


async def loaded(persona_id: str) -> Outcome[dict]:
    """Return the live persona from the in-process registry."""
    await bus.propose("Getting loaded persona", {"persona_id": persona_id})
    try:
        p = agents.find(persona_id)
        return Outcome(success=True, message="", data={"persona": p})
    except MindError as e:
        await bus.broadcast("Loaded persona not found", {"persona_id": persona_id})
        return Outcome(success=False, message=str(e))
