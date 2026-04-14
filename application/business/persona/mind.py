"""Persona — reading the cognitive state of a persona."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents, bus
from application.core.data import Persona
from application.core.exceptions import MindError
from application.platform.objects import json as to_json

from .loaded import loaded


@dataclass
class MindData:
    messages: list
    meaning: str
    plan: str
    context: str


async def mind(persona: Persona) -> Outcome[MindData]:
    """Return the current memory state — messages, meaning, plan, and context."""
    await bus.propose("Getting persona mind", {"persona": persona})
    result = await loaded(persona)
    if not result.success:
        return result
    try:
        ego = agents.persona(result.data.persona)
        memory = ego.memory

        await bus.broadcast("Persona mind loaded", {"persona": persona})
        return Outcome(success=True, message="", data=MindData(
            messages=[to_json(m) for m in memory.messages],
            meaning=memory.meaning,
            plan=memory.plan,
            context=memory.context,
        ))
    except MindError as e:
        await bus.broadcast("Reading persona mind failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
