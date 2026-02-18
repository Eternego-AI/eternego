"""Data models for the application."""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from application.core import paths


@dataclass(kw_only=True)
class Channel:
    name: str
    credentials: dict | None = None


@dataclass(kw_only=True)
class Model:
    name: str
    provider: str | None = None
    credentials: dict | None = None


@dataclass(kw_only=True)
class Thought:
    intent: str
    content: str = ""
    tool_calls: list[dict] | None = None



class Thinking:
    """The thinking process — wraps a reasoning function to yield thoughts."""

    def __init__(self, reason_by: Callable[[], AsyncIterator["Thought"]]):
        self._reason = reason_by

    def reason(self) -> AsyncIterator["Thought"]:
        return self._reason()


@dataclass(kw_only=True)
class Observation:
    facts: list[str]
    traits: list[str]
    context: list[str]
    struggles: list[str]


class Gateway:
    """A live channel connection — a thread bound to a channel."""

    def __init__(self, channel: Channel, threading: ModuleType):
        self.channel = channel
        self.threading = threading
        self._stopped = threading.Event()

    @property
    def is_stopped(self) -> bool:
        return self._stopped.is_set()

    def close(self):
        self._stopped.set()


@dataclass(kw_only=True)
class Persona:
    id: str
    name: str
    model: Model
    base_model: str = ""
    frontier: Model | None = None
    channels: list[Channel] | None = None

    @property
    def storage_dir(self) -> Path:
        return paths.agents_home() / self.id
