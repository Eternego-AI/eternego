"""Memory — the mind's stream of messages."""

from application.core import paths
from application.core.data import Channel, Message, Prompt
from application.platform import logger, persistent_memory
from application.platform.objects import json as to_json


class Memory:
    """Per-persona message history with disk persistence."""

    def __init__(self, persona):
        self._persona = persona
        self._messages: list[Message] = []
        self.meaning: str | None = None
        self.plan: dict | None = None
        self.context: str | None = None
        self._storage_id = f"mind:{persona.id}"
        path = paths.mind(persona.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        persistent_memory.load(self._storage_id, path)

    def remember(self) -> None:
        """Restore messages and context from persisted state."""
        logger.debug("memory.remember", {"persona": self._persona.id, "messages": self._messages})
        entries = persistent_memory.read(self._storage_id)
        if not entries:
            return
        state = entries[0]
        for m in state.get("messages", []):
            channel_data = m.get("channel")
            channel = None
            if channel_data:
                channel = Channel(
                    type=channel_data.get("type", ""),
                    name=channel_data.get("name", ""),
                    credentials=channel_data.get("credentials"),
                    verified_at=channel_data.get("verified_at"),
                )
            prompt_data = m.get("prompt")
            prompt = None
            if prompt_data:
                prompt = Prompt(
                    role=prompt_data.get("role", ""),
                    content=prompt_data.get("content", ""),
                )
            self._messages.append(Message(
                content=m.get("content", ""),
                channel=channel,
                prompt=prompt,
                id=m.get("id", ""),
            ))
        self.context = state.get("context")

    def persist(self) -> None:
        """Save messages and context to disk."""
        logger.debug("memory.persist", {"persona": self._persona.id, "messages": self._messages})
        state = {
            "messages": [to_json(m) for m in self._messages],
            "context": self.context,
        }
        persistent_memory.clear(self._storage_id)
        persistent_memory.append(self._storage_id, state)

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def prompts(self) -> list[dict]:
        return [{"role": m.prompt.role, "content": m.prompt.content} for m in self._messages]

    def add(self, message: Message) -> None:
        self._messages.append(message)

    def clear(self) -> None:
        self._messages = []
