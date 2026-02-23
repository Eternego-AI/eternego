"""Memories — persona-scoped short-term memory, persisted to disk."""

import uuid

from application.platform import persistent_memory
from application.core import paths
from application.core.data import Persona, Thread

_threads: dict[str, Thread] = {}  # persona_id → current public thread


def _current_thread(persona_id: str) -> Thread:
    if persona_id not in _threads:
        _threads[persona_id] = Thread(id=str(uuid.uuid4()))
    return _threads[persona_id]


def _rotate_thread(persona_id: str) -> Thread:
    _threads[persona_id] = Thread(id=str(uuid.uuid4()))
    return _threads[persona_id]


def agent(persona: Persona) -> "AgentMemory":
    """Return the memory handle for this persona."""
    persistent_memory.load(persona.id, paths.home(persona.id) / "memory.json")
    return AgentMemory(persona)


class AgentMemory:
    """Handle for one persona's memory. Use via memories.agent(persona)."""

    def __init__(self, persona: Persona):
        self._persona = persona

    def remember(self, document: dict) -> Thread:
        """Append a document to the current thread. Returns the Thread."""
        thread = _current_thread(self._persona.id)
        persistent_memory.append(self._persona.id, {**document, "thread_id": thread.id})
        return thread

    def remember_on(self, thread: Thread, document: dict) -> Thread:
        """Append a document to a specific thread. Returns the Thread."""
        persistent_memory.append(self._persona.id, {**document, "thread_id": thread.id})
        return thread

    def remove_from_thread(self, content: str, thread_id: str) -> None:
        """Remove documents matching content from a specific thread."""
        persistent_memory.remove_where(
            self._persona.id,
            lambda doc: doc.get("thread_id") == thread_id and doc.get("content") == content,
        )

    def private_thread(self) -> Thread:
        """Create a new private thread without affecting the current public thread."""
        return Thread(id=str(uuid.uuid4()), public=False)

    def new_thread(self) -> Thread:
        """Rotate to a new public thread and return it."""
        return _rotate_thread(self._persona.id)

    def current_thread(self) -> Thread:
        """Return the current public thread."""
        return _current_thread(self._persona.id)

    def forget_everything(self) -> None:
        """Clear all memory for this persona and rotate to a fresh thread."""
        persistent_memory.clear(self._persona.id)
        _rotate_thread(self._persona.id)

    def hash(self) -> str:
        """Return a hash of the current memory state."""
        return persistent_memory.load(self._persona.id, paths.home(self._persona.id) / "memory.json")

    def verify(self, current_hash: str) -> bool:
        """Return True if memory is unchanged since the given hash was taken."""
        return persistent_memory.verify(self._persona.id, current_hash)

    def threads(self) -> list[Thread]:
        """Return all threads present in memory, in order of first appearance."""
        docs = persistent_memory.filter_by(self._persona.id, lambda doc: "thread_id" in doc)
        seen = dict.fromkeys(doc["thread_id"] for doc in docs)
        return [Thread(id=thread_id) for thread_id in seen]

    def as_messages(self, thread_id: str | None = None) -> list[dict]:
        """Return memory as LLM chat messages, optionally filtered by thread_id."""
        if thread_id:
            docs = persistent_memory.filter_by(
                self._persona.id, lambda doc: doc.get("thread_id") == thread_id
            )
            return [{"role": doc["role"], "content": doc["content"]} for doc in docs]

        messages = []
        for doc in persistent_memory.read(self._persona.id):
            doc_type = doc.get("type")
            if doc_type in ("stimulus", "reflection", "prediction"):
                messages.append({"role": doc["role"], "content": doc["content"]})
            elif doc_type == "act":
                messages.append({"role": "assistant", "content": "", "tool_calls": doc["tool_calls"]})
                messages.append({"role": "tool", "content": doc["result"]})
            elif doc_type == "say":
                messages.append({"role": "assistant", "content": doc["content"]})
        return messages

