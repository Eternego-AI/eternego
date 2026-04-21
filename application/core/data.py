"""Data models for the application."""

import uuid
from dataclasses import dataclass, field
from datetime import date

from application.platform.objects import Data, hidden, sensitive


@dataclass(kw_only=True)
class Model(Data):
    name: str
    provider: str | None = None
    api_key: str | None = sensitive()
    url: str


@dataclass(kw_only=True)
class Channel(Data):
    type: str
    name: str = ""          # chat_id for telegram, channel_id for discord, persona_id for web
    credentials: dict | None = sensitive()
    verified_at: str | None = None


@dataclass(kw_only=True)
class Persona(Data):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    thinking: Model
    version: str = "v1"
    base_model: str = ""
    birthday: str = field(default_factory=lambda: str(date.today()))
    status: str = "active"
    vision: Model | None = None
    frontier: Model | None = None
    channels: list[Channel] | None = None


@dataclass(kw_only=True)
class Prompt(Data):
    role: str
    content: str


@dataclass(kw_only=True)
class Media(Data):
    source: str
    caption: str


@dataclass(kw_only=True)
class Message(Data):
    content: str
    channel: Channel | None = None
    prompt: Prompt | None = None
    media: Media | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(kw_only=True)
class Thread(Data):
    id: str
    public: bool = True


@dataclass(kw_only=True)
class Observation:
    facts: list[str]
    traits: list[str]
    context: list[str]
    struggles: list[str]


