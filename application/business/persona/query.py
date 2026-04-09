"""Persona — answering a direct query."""

from application.business.outcome import Outcome
from application.core import agents, bus, models
from application.core.brain import situation
from application.core.data import Persona
from application.core.exceptions import MindError


async def query(persona: Persona, messages) -> Outcome[dict]:
    """Answer a direct query using the local model — no pipeline, no memory."""
    await bus.propose("Querying", {"persona": persona})
    try:
        if agents.persona(persona).current_situation is situation.sleep:
            await bus.broadcast("Queried", {"persona": persona})
            return Outcome(success=True, message="", data={"response": f"{persona.name} is sleeping."})

        ego = agents.persona(persona)

        response = await models.chat(persona.thinking, [
            {"role": "system", "content": ego.identity()},
            messages,
        ])

        await bus.broadcast("Queried", {"persona": persona})
        return Outcome(success=True, message="", data={"response": response})
    except MindError as e:
        await bus.broadcast("Query failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
