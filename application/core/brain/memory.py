"""Memory — the mind's stream of messages, known meanings, and carried context.

Messages and context cross sleep (they're what the persona carries forward).
Cognitive state — what kind of moment she's in, what she's doing — lives in
the message stream itself as cognitive signals: the persona's expressed
`intention` and the `impression` she received in answer.

Cognitive functions speak in introspective verbs. Recognize calls
`memory.intention(text)` to express what kind of moment she's in. Learn
reads `memory.perception()` to find the pending intention, fetches the
matching procedure, calls `memory.impression(body)` to record what she
now holds. Decide reads `memory.comprehension()` to find a freshly-
delivered impression. The wire shape of those signals (assistant JSON
tool-call, user TOOL_RESULT) stays inside memory; cognitive functions
don't see it.

Known meanings live here too — the persona has its instructions by heart,
not re-discovered every tick. They're loaded from disk at construction;
learned meanings join them immediately via `learn()`; next start re-reads.
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
    lost across a crash. Cognitive state lives in the message stream — see
    `perception` and `comprehension` for reading the cognitive signals.
    """

    def __init__(self, persona):
        self._persona = persona
        self._messages: list[Message] = []
        self._archive: list[list[Message]] = []
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
                        question=media_data.get("question", ""),
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
    def context(self) -> str | None:
        return self._context

    @context.setter
    def context(self, value: str | None) -> None:
        logger.debug("memory.context", {"persona": self._persona.id, "value": value})
        self._context = value
        self._persist()

    @property
    def context_prompt(self) -> list[Prompt]:
        """Recent Context as a system Prompt, or empty list if no context.
        Composable with `ego.identity` to form the full identity prefix."""
        text = (self._context or "").strip()
        if not text:
            return []
        return [Prompt(role="system", content="## Recent Context\n\n" + text)]

    def remember(self, message: Message) -> None:
        """Add a message to the mind."""
        logger.debug("memory.remember", {"persona": self._persona.id, "message": message})
        self._messages.append(message)
        self._persist()

    def intention(self, text: str) -> None:
        """Express an intention to learn how to be in a kind of moment.
        Recognize calls this when she names what kind of moment she sees.

        Stored on the wire as an assistant `tools.load_instruction` call
        with the intention as its argument; cognitive callers don't see
        that shape — they just say `memory.intention("Posting To X")`."""
        call = json.dumps({"tools.load_instruction": {"intention": text}})
        self.remember(Message(content=call, prompt=Prompt(role="assistant", content=call)))

    def perception(self) -> str | None:
        """The intention currently awaiting a procedure, or None.
        Learn reads this to know what to fetch.

        Walks back through recent messages; if the most recent cognitive
        signal is a pending intention (no impression delivered after it),
        returns the intention text. Returns None if anything else is the
        most recent signal — already-resolved intention, plain
        conversation, no signals at all.

        Skips assistant prose so narration alongside an intention call
        doesn't hide it from the gate."""
        for msg in reversed(self._messages):
            if not msg.prompt or not isinstance(msg.prompt.content, str):
                continue
            content = msg.prompt.content
            role = msg.prompt.role
            if role == "assistant":
                try:
                    obj = json.loads(content)
                except json.JSONDecodeError:
                    continue  # prose — keep scanning
                if isinstance(obj, dict) and "tools.load_instruction" in obj:
                    args = obj["tools.load_instruction"]
                    if isinstance(args, dict):
                        text = str(args.get("intention", "")).strip()
                        return text or None
                return None  # other tool call — boundary
            if role == "user":
                return None  # any user message is a boundary
        return None

    def impression(self, body: str) -> None:
        """Record a procedure as the impression matching the pending
        intention. Learn calls this to deliver the procedure into the
        conversation.

        Stored on the wire as a user TOOL_RESULT for `load_instruction`;
        cognitive callers don't see that shape — they just say
        `memory.impression(procedure_body)`."""
        text = f"TOOL_RESULT\ntool: load_instruction\nstatus: ok\nresult: {body}"
        self.remember(Message(content=text, prompt=Prompt(role="user", content=text)))

    def comprehension(self) -> str | None:
        """The procedure body she just received, or None.
        Decide reads this to gate on whether to act on a fresh impression.

        Walks back through recent messages; if the most recent signal is
        an impression delivering a procedure, returns the procedure body.
        Returns None for any other state.

        Skips assistant prose so narration after the impression doesn't
        hide it from the gate."""
        for msg in reversed(self._messages):
            if not msg.prompt or not isinstance(msg.prompt.content, str):
                continue
            content = msg.prompt.content
            role = msg.prompt.role
            if role == "assistant":
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    continue  # prose — keep scanning
                return None  # tool call (any) — not an impression
            if role == "user":
                if not content.startswith("TOOL_RESULT"):
                    return None  # plain user message — boundary
                tool_name = None
                for line in content.splitlines():
                    if line.startswith("tool:"):
                        tool_name = line[len("tool:"):].strip()
                        break
                if tool_name != "load_instruction":
                    return None  # different tool's result — boundary
                marker = "\nresult: "
                idx = content.find(marker)
                if idx < 0:
                    return None
                body = content[idx + len(marker):]
                return body or None
        return None

    def add_tool_result(self, selector: str, value, status: str, result: str, media: Media | None = None) -> None:
        """Persist a mechanical tool invocation as the standard pair: an
        assistant message naming the call followed by a user message
        carrying the TOOL_RESULT.

        Used by clock's executor for tools that touch the world. Cognitive
        signals (intention/impression) go through their dedicated methods;
        this one is for tools/abilities the executor actually runs.

        `value` can be a dict (args), None (for null-valued specials), or
        any JSON-serializable value — whatever the model originally produced
        as the selector's value.

        When `media` is given (e.g. screenshot from take_screenshot), the
        TOOL_RESULT text travels as the media's caption and Prompt is left
        unset — realize hands the image to the eye on the next tick and
        the answer arrives as a tools.vision pair."""
        call = json.dumps({selector: value})
        self.remember(Message(content=call, prompt=Prompt(role="assistant", content=call)))
        name = selector.split(".", 1)[1] if "." in selector else selector
        text = f"TOOL_RESULT\ntool: {name}\nstatus: {status}\nresult: {result}"
        if media:
            self.remember(Message(content=text, media=Media(source=media.source, caption=text, question=media.question)))
        else:
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
