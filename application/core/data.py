"""Data models for the application."""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path


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


class Memory:
    """Short-term memory — holds documents from the current session."""

    def __init__(self):
        self._documents: list[dict] = []

    def append(self, document: dict) -> None:
        self._documents.append(document)

    def __iter__(self):
        return iter(self._documents)


@dataclass(kw_only=True)
class Observation:
    facts: list[str]
    traits: list[str]
    context: list[str]


@dataclass(kw_only=True)
class Persona:
    id: str
    name: str
    model: Model
    frontier: Model | None = None
    channels: list[Channel] | None = None

    @property
    def storage_dir(self) -> Path:
        return Path.home() / ".eternego" / "personas" / self.id
