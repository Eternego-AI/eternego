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
        """Clear all memory for this persona."""
        _storage[self._persona.id] = []

    def as_messages(self) -> list[dict]:
        """Return memory formatted as LLM chat messages."""
        messages = []
        for doc in _storage.get(self._persona.id, []):
            doc_type = doc.get("type")
            if doc_type in ("stimulus", "reflection", "prediction"):
                messages.append({"role": doc["role"], "content": doc["content"]})
            elif doc_type == "act":
                messages.append({"role": "assistant", "content": "", "tool_calls": doc["tool_calls"]})
                messages.append({"role": "tool", "content": doc["result"]})
            elif doc_type == "say":
                messages.append({"role": "assistant", "content": doc["content"]})
        return messages

    def as_transcript(self) -> str:
        """Return memory formatted as a numbered conversation transcript."""
        lines = []
        idx = 1
        for doc in _storage.get(self._persona.id, []):
            doc_type = doc.get("type")
            if doc_type == "stimulus" and doc.get("role") == "user":
                lines.append(f"[{idx}] User: {doc['content']}")
                idx += 1
            elif doc_type == "say":
                lines.append(f"[{idx}] Persona: {doc['content']}")
                idx += 1
            elif doc_type == "act":
                tool_calls = doc.get("tool_calls", [])
                tool_name = tool_calls[0]["function"]["name"] if tool_calls else "tool"
                result = str(doc.get("result", ""))[:300]
                lines.append(f"[{idx}] Action ({tool_name}): {result}")
                idx += 1
        return "\n".join(lines)
