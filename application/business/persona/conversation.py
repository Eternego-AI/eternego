"""Persona — reading conversation history."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Persona


@dataclass
class ConversationData:
    messages: list


async def conversation(persona: Persona) -> Outcome[ConversationData]:
    """Return the conversation history for a persona."""
    await bus.propose("Reading conversation", {"persona": persona})
    try:
        messages = paths.read_jsonl(paths.conversation(persona.id))
        await bus.broadcast("Conversation read", {"persona": persona})
        return Outcome(success=True, message="", data=ConversationData(messages=messages))
    except Exception as e:
        await bus.broadcast("Conversation read failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
