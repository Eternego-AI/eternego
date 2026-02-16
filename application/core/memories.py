"""Memories — persona-scoped short-term memory, process-lived."""

from application.core.data import Persona

# Static storage: one dict for the process, created at import.
_storage: dict[str, list[dict]] = {}


def agent(persona: Persona) -> "AgentMemory":
    """Return the memory handle for this persona (creates on first use)."""
    return AgentMemory(persona)


class AgentMemory:
    """Handle for one persona's memory. Use via memories.agent(persona)."""

    def __init__(self, persona: Persona):
        self._persona = persona

    def remember(self, document: dict) -> None:
        """Append a document. Creates memory for the persona if needed."""
        _storage.setdefault(self._persona.id, []).append(document)

    def forget_everything(self) -> None:
        """Clear all memory for this persona. Creates memory if needed."""
        _storage[self._persona.id] = []

    def recall(self) -> list[dict]:
        """Return all memory for this persona (a copy). Creates memory if needed."""
        return list(_storage.setdefault(self._persona.id, []))
