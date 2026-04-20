"""Memory — the mind's stream of messages, known meanings, and carried context.

Messages and context cross sleep (they're what the persona carries forward). Meaning
and plan are ephemeral — they belong to one pass of cognition. On wake, the situation
has changed; last night's meaning or plan no longer applies. The persona decides again
from the messages and context it has now. Known meanings live here too — the persona
has its abilities by heart, not re-discovered every tick. They're loaded from disk at
construction; learned meanings join them immediately via learn(); next start re-reads.
"""

from application.core import paths
from application.core.brain import meanings as _meanings
from application.core.data import Channel, Media, Message, Prompt
from application.platform import logger, persistent_memory
from application.platform.objects import json as to_json


class Memory:
    """Per-persona mind state.

    Mutations to messages and context persist to disk immediately so nothing is
    lost across a crash. Meaning and plan are in-memory only — recomputed every
    cognitive pass and never carried across sleep.
    """

    def __init__(self, persona):
        self._persona = persona
        self._messages: list[Message] = []
        self._meaning: str | None = None
        self._plan: dict | None = None
        self._context: str | None = None
        self._meanings: dict = _meanings.available(persona)
        self._storage_id = f"mind:{persona.id}"
        path = paths.memory(persona.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        persistent_memory.load(self._storage_id, path)
        entries = persistent_memory.read(self._storage_id)
        if entries:
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
                media_data = m.get("media")
                media = None
                if media_data:
                    media = Media(
                        source=media_data.get("source", ""),
                        caption=media_data.get("caption", ""),
                    )
                self._messages.append(Message(
                    content=m.get("content", ""),
                    channel=channel,
                    prompt=prompt,
                    media=media,
                    id=m.get("id", ""),
                ))
            self._context = state.get("context")

    def _persist(self) -> None:
        logger.debug("memory._persist", {"persona": self._persona.id})
        state = {
            "messages": [to_json(m) for m in self._messages],
            "context": self._context,
        }
        persistent_memory.clear(self._storage_id)
        persistent_memory.append(self._storage_id, state)

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def prompts(self) -> list[dict]:
        return [{"role": m.prompt.role, "content": m.prompt.content} for m in self._messages if m.prompt]

    @property
    def meaning(self) -> str | None:
        return self._meaning

    @meaning.setter
    def meaning(self, value: str | None) -> None:
        logger.debug("memory.meaning", {"persona": self._persona.id, "value": value})
        self._meaning = value

    @property
    def plan(self) -> dict | None:
        return self._plan

    @plan.setter
    def plan(self, value: dict | None) -> None:
        logger.debug("memory.plan", {"persona": self._persona.id, "value": value})
        self._plan = value

    @property
    def context(self) -> str | None:
        return self._context

    @context.setter
    def context(self, value: str | None) -> None:
        logger.debug("memory.context", {"persona": self._persona.id, "value": value})
        self._context = value
        self._persist()

    def remember(self, message: Message) -> None:
        """Add a message to the mind."""
        logger.debug("memory.remember", {"persona": self._persona.id, "message": message})
        self._messages.append(message)
        self._persist()

    def forget(self) -> None:
        """Clear all messages. Context is preserved."""
        logger.debug("memory.forget", {"persona": self._persona.id})
        self._messages = []
        self._persist()

    @property
    def meanings(self) -> dict:
        return dict(self._meanings)

    def learn(self, name: str, instance) -> None:
        """Add a newly-created meaning to the persona's known abilities."""
        logger.debug("memory.learn", {"persona": self._persona.id, "name": name})
        self._meanings[name] = instance

    def unlearn(self, name: str) -> None:
        """Remove a meaning from the persona's known abilities."""
        logger.debug("memory.unlearn", {"persona": self._persona.id, "name": name})
        self._meanings.pop(name, None)

    def distill(self, context: str) -> None:
        """Fold the stream down to its essence: replace messages with a new context.
        Empty context preserves the old one — a failed reflect still drains memory
        but doesn't overwrite what the persona already carried forward."""
        logger.debug("memory.distill", {"persona": self._persona.id, "context": context})
        if context:
            self._context = context
        self._messages = []
        self._persist()
