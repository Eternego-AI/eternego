"""Data models for the application."""

import inspect
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from application.core import paths
from application.platform.objects import Data, sensitive


@dataclass(kw_only=True)
class Model(Data):
    name: str
    provider: str | None = None
    credentials: dict | None = sensitive()


@dataclass(kw_only=True)
class Persona(Data):
    id: str
    name: str
    model: Model
    base_model: str = ""
    frontier: Model | None = None
    networks: list[Network] | None = None

    @property
    def storage_dir(self) -> Path:
        return paths.agents_home() / self.id


@dataclass(kw_only=True)
class Network(Data):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    credentials: dict | None = sensitive()


@dataclass(kw_only=True)
class Channel:
    type: str
    name: str  # e.g. chat_id for telegram, uuid for web


@dataclass(kw_only=True)
class Message(Data):
    channel: Channel
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(kw_only=True)
class Thread:
    id: str
    public: bool = True


@dataclass(kw_only=True)
class Prompt:
    role: str
    content: str



@dataclass(kw_only=True)
class Observation:
    facts: list[str]
    traits: list[str]
    context: list[str]
    struggles: list[str]


class Gateway:
    """A live conversation channel — routes messages to a specific destination."""

    def __init__(
        self,
        channel: Channel,
        *,
        send: Callable[[str], None] | None = None,
        stop: Callable[[], None] | None = None,
        wait: Callable[[], None] | None = None,
        verify: Callable[[], bool] | None = None,
    ):
        self.channel = channel
        self._send = send or (lambda text: None)
        self._stop = stop or (lambda: None)
        self._wait = wait or (lambda: None)
        self._verify = verify or (lambda: True)

    async def send(self, text: str) -> None:
        result = self._send(text)
        if inspect.isawaitable(result):
            await result

    async def stop(self) -> None:
        result = self._stop()
        if inspect.isawaitable(result):
            await result

    async def wait(self):
        result = self._wait()
        if inspect.isawaitable(result):
            return await result

    def verify(self) -> bool:
        return self._verify()

