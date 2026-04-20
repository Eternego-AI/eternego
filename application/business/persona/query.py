"""Persona — answering a direct query."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, models
from application.core.data import Persona
from application.core.exceptions import EngineConnectionError, MindError


@dataclass
class QueryData:
    response: str


async def query(persona: Persona, messages) -> Outcome[QueryData]:
    """Answer a direct query using the local model — no pipeline, no memory."""
    bus.propose("Querying", {"persona": persona, "messages": messages})
    try:
        if persona.ego.is_sleeping():
            bus.broadcast("Queried", {"persona": persona})
            return Outcome(success=True, message="", data=QueryData(response=f"{persona.name} is sleeping."))

        response = await models.chat(persona.thinking, persona.ego.identity(), [], messages)

        bus.broadcast("Queried", {"persona": persona})
        return Outcome(success=True, message="", data=QueryData(response=response))
    except EngineConnectionError as e:
        bus.broadcast("Query failed", {"persona": persona, "reason": "connection", "error": str(e)})
        return Outcome(success=False, message=str(e))
    except MindError as e:
        bus.broadcast("Query failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
