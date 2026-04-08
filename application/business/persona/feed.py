"""Persona — feeding external AI history."""

from application.business.outcome import Outcome
from application.core import agents, bus, models
from application.core.data import Persona
from application.core.exceptions import EngineConnectionError, FrontierError


async def feed(persona: Persona, data: str, source: str) -> Outcome[dict]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona": persona, "source": source})

    try:
        messages = await models.read_external_history(data, source)
        conversation_text = "\n".join(
            f"{'Person' if m['role'] == 'user' else 'Persona'}: {m['content']}"
            for m in messages
        )
        await agents.persona(persona).learn(conversation_text)

        await bus.broadcast("Persona fed", {"persona": persona, "source": source})
        return Outcome(
            success=True,
            message="Persona fed successfully",
            data={"persona_id": persona.id},
        )

    except FrontierError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")
