"""Persona — answering a direct query."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, models
from application.core.data import Persona
from application.core.exceptions import MindError


@dataclass
class QueryData:
    response: str


async def query(persona: Persona, messages) -> Outcome[QueryData]:
    """Answer a direct query using the local model — no pipeline, no memory."""
    await bus.propose("Querying", {"persona": persona, "messages": messages})
    try:
        if persona.ego.is_sleeping():
            await bus.broadcast("Queried", {"persona": persona})
            return Outcome(success=True, message="", data=QueryData(response=f"{persona.name} is sleeping."))

        response = await models.chat(persona.thinking, [
            {"role": "system", "content": persona.ego.identity()},
            messages,
        ])

        await bus.broadcast("Queried", {"persona": persona})
        return Outcome(success=True, message="", data=QueryData(response=response))
    except MindError as e:
        await bus.broadcast("Query failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
