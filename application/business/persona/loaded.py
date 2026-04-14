"""Persona — getting a loaded persona from the registry."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents, bus
from application.core.data import Persona
from application.core.exceptions import MindError


@dataclass
class LoadedData:
    persona: Persona


async def loaded(persona: Persona) -> Outcome[LoadedData]:
    """Return the live persona from the in-process registry."""
    await bus.propose("Getting loaded persona", {"persona": persona})
    try:
        p = agents.find(persona.id)
        return Outcome(success=True, message="", data=LoadedData(persona=p))
    except MindError as e:
        await bus.broadcast("Loaded persona not found", {"persona": persona})
        return Outcome(success=False, message=str(e))
