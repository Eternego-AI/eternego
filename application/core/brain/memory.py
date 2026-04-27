"""Memory — the mind's stream of messages, known meanings, and carried context.

Messages and context cross sleep (they're what the persona carries forward). Impression,
ability, meaning, and plan are ephemeral — they belong to one pass of cognition. On
wake, the situation has changed; last night's impression or plan no longer applies.
The persona decides again from the messages and context it has now. Known meanings
live here too — the persona has its abilities by heart, not re-discovered every tick.
They're loaded from disk at construction; learned meanings join them immediately via
learn(); next start re-reads.
"""

import json

from application.core import paths
from application.core.brain import meanings as _meanings
from application.core.data import Channel, Media, Message, Prompt
from application.platform import logger, persistent_memory
from application.platform.objects import json as to_json


class Memory:
    """Per-persona mind state.

    Mutations to messages and context persist to disk immediately so nothing is
    lost across a crash. Impression, ability, and meaning are in-memory only —
    recomputed every cognitive pass and never carried across sleep.
    """

    def __init__(self, persona):
        self._persona = persona
        self._messages: list[Message] = []
        self._archive: list[list[Message]] = []
        self._impression: str | None = None
        self._ability: int = 0
        self._meaning: str | None = None
        self._context: str | None = None
        self._builtin_meanings: dict = _meanings.builtin(persona)
        self._custom_meanings: dict = _meanings.custom(persona)
        self._storage_id = f"mind:{persona.id}"
        self._load()

    def _load(self) -> None:
        """Read persistent state from disk into this Memory. Subclasses
        override to skip (PastMemory does)."""
        path = paths.memory(self._persona.id)
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
            for batch in state.get("archive", []):
                restored_batch = []
                for m in batch:
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
                    restored_batch.append(Message(
                        content=m.get("content", ""),
                        channel=channel,
                        prompt=prompt,
                        media=media,
                        id=m.get("id", ""),
                    ))
                self._archive.append(restored_batch)
            self._context = state.get("context")

    def _persist(self) -> None:
        """Write current state to disk. Subclasses override to skip
        (PastMemory does)."""
        logger.debug("memory._persist", {"persona": self._persona.id})
        state = {
            "messages": [to_json(m) for m in self._messages],
            "archive": [[to_json(m) for m in batch] for batch in self._archive],
            "context": self._context,
        }
        persistent_memory.clear(self._storage_id)
        persistent_memory.append(self._storage_id, state)

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def prompts(self) -> list[Prompt]:
        """The messages shaped for the model as a list of Prompts, with the
        cache breakpoint attached to the last entry only. Callers should not
        manage cache state — it is recomputed on every read, so memory always
        cooperates with Anthropic's cache_control limits."""
        result: list[Prompt] = []
        for m in self._messages:
            if not m.prompt:
                continue
            result.append(Prompt(role=m.prompt.role, content=m.prompt.content))
        if result:
            result[-1].cache_point = True
        return result

    @property
    def impression(self) -> str | None:
        return self._impression

    @impression.setter
    def impression(self, value: str | None) -> None:
        logger.debug("memory.impression", {"persona": self._persona.id, "value": value})
        self._impression = value

    @property
    def ability(self) -> int:
        return self._ability

    @ability.setter
    def ability(self, value: int) -> None:
        logger.debug("memory.ability", {"persona": self._persona.id, "value": value})
        self._ability = value

    @property
    def meaning(self) -> str | None:
        return self._meaning

    @meaning.setter
    def meaning(self, value: str | None) -> None:
        logger.debug("memory.meaning", {"persona": self._persona.id, "value": value})
        self._meaning = value

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

    def add_tool_result(self, selector: str, value, status: str, result: str) -> None:
        """Persist a tool/ability/special invocation as the standard pair: an
        assistant message naming the call (in the same JSON shape the model
        emits) followed by a user message carrying the TOOL_RESULT.

        `value` can be a dict (args), None (for null-valued specials like
        `clear_memory` or `stop`), or any JSON-serializable value — whatever
        the model originally produced as the selector's value. Centralizing
        the convention here keeps memory legible to the persona on its next
        read: it sees its own request right before the result."""
        name = selector.split(".", 1)[1] if "." in selector else selector
        call = json.dumps({selector: value})
        self.remember(Message(content=call, prompt=Prompt(role="assistant", content=call)))
        text = f"TOOL_RESULT\ntool: {name}\nstatus: {status}\nresult: {result}"
        self.remember(Message(content=text, prompt=Prompt(role="user", content=text)))

    def forget(self) -> None:
        """Clear all messages. Context is preserved."""
        logger.debug("memory.forget", {"persona": self._persona.id})
        self._messages = []
        self._persist()

    @property
    def meanings(self) -> dict:
        return {**self._builtin_meanings, **self._custom_meanings}

    @property
    def builtin_meanings(self) -> dict:
        return dict(self._builtin_meanings)

    @property
    def custom_meanings(self) -> dict:
        return dict(self._custom_meanings)

    def learn(self, name: str, instance) -> None:
        """Add a newly-created meaning to the persona's custom abilities."""
        logger.debug("memory.learn", {"persona": self._persona.id, "name": name})
        self._custom_meanings[name] = instance

    def unlearn(self, name: str) -> None:
        """Remove a custom meaning from the persona's known abilities."""
        logger.debug("memory.unlearn", {"persona": self._persona.id, "name": name})
        self._custom_meanings.pop(name, None)

    @property
    def archive(self) -> list[list[Message]]:
        return list(self._archive)

    def archive_messages(self) -> None:
        """Move current messages to archive as a batch."""
        logger.debug("memory.archive_messages", {"persona": self._persona.id})
        if self._messages:
            self._archive.append(list(self._messages))
            self._persist()

    def clear_archive(self) -> None:
        """Clear all archived batches. Called by sleep."""
        logger.debug("memory.clear_archive", {"persona": self._persona.id})
        self._archive = []
        self._persist()
