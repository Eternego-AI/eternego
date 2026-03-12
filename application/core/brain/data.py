"""Brain data models — Signal, Perception, Thought, Meaning."""

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from application.platform import datetimes


@dataclass
class Signal:
    """Atomic unit of communication."""
    id: str
    role: str               # user | assistant | system
    content: str
    channel_type: str = ""
    channel_name: str = ""
    message_id: str = ""
    created_at: datetime = field(default_factory=datetimes.now)


@dataclass
class Perception:
    """A group of related Signals forming a thread. Impression is the unique key."""
    impression: str
    thread: list[Signal] = field(default_factory=list)


class Meaning(ABC):
    """Abstract base for all meanings — what a perception means to the persona."""
    name: str

    def __init__(self, persona):
        self.persona = persona

    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def clarification(self) -> str: ...

    @abstractmethod
    def reply(self) -> str: ...

    @abstractmethod
    def path(self) -> str | None: ...

    async def run(self, persona_response: dict):
        """Default runner — dispatches tool calls via the adaptor.

        One tool call per step. Result always returned as a Signal.
        The model sees the output and decides: continue, retry, or done.
        Built-in meanings can override this with specific logic.
        """
        from application.core import tools
        tool_name = persona_response.get("tool")
        if not tool_name:
            return None
        params = {k: v for k, v in persona_response.items() if k != "tool"}
        result = await tools.call(tool_name, **params)
        return Signal(id=str(uuid.uuid4()), role="user", content=result)


@dataclass
class Thought:
    """A Perception with a matched Meaning — the cognitive work unit."""
    perception: Perception
    meaning: Meaning
    priority: int = 0       # importance rank; higher = more important
    id: str = ""
    processed_at: datetime | None = None

    def __post_init__(self):
        if not self.id:
            raw = f"{self.perception.impression}:{len(self.perception.thread)}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:12]
