"""Persona — reading conversation history."""

from application.business.outcome import Outcome
from application.core import bus, paths


async def conversation(persona_id: str) -> Outcome[dict]:
    """Return the conversation history for a persona."""
    await bus.propose("Reading conversation", {"persona_id": persona_id})
    try:
        messages = paths.read_jsonl(paths.conversation(persona_id))
        await bus.broadcast("Conversation read", {"persona_id": persona_id})
        return Outcome(success=True, message="", data={"messages": messages})
    except Exception as e:
        await bus.broadcast("Conversation read failed", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message=str(e))
