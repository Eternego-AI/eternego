"""Data models for the application."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import date

from application.platform.objects import Data, hidden, sensitive


@dataclass(kw_only=True)
class Model(Data):
    name: str
    provider: str | None = None
    credentials: dict | None = sensitive()


@dataclass(kw_only=True)
class Channel(Data):
    type: str
    name: str = ""          # chat_id for telegram, uuid for web; empty for network-level channels
    credentials: dict | None = sensitive()
    verified_at: str | None = None
    bus: asyncio.Queue | None = hidden()


@dataclass(kw_only=True)
class Persona(Data):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    model: Model
    version: str = "v1"
    base_model: str = ""
    birthday: str = field(default_factory=lambda: str(date.today()))
    frontier: Model | None = None
    channels: list[Channel] | None = None


@dataclass(kw_only=True)
class Message(Data):
    channel: Channel
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(kw_only=True)
class Thread(Data):
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


