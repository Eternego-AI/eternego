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
    idle_timeout: int = 3600
    vision: Model | None = None
    frontier: Model | None = None
    channels: list[Channel] | None = None


@dataclass(kw_only=True)
class Prompt(Data):
    role: str
    content: str | list
    cache_point: bool = False


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


@dataclass(kw_only=True)
class Action:
    """A cognitive function's declaration of what JSON it expects from the model.

    Recursive: `fields` are themselves Actions. A leaf has empty `fields`
    and a primitive `type`. An object has `type="object"` and a populated
    `fields` list. An array has `type="array"` and an `items` Action.

    `required` says whether *this* Action is required at the level where
    it appears as a field. `one_of=True` on an object Action means
    exactly one of its `fields` must be present (a union type).

    `name` identifies an Action where it appears as a property key (in
    object fields) or as the function name on the wire. Array items and
    inline anonymous shapes can omit it.

    The class itself is provider-agnostic. Translation to each
    provider's native tool-call shape lives in `core.actions`.
    """
    name: str = ""
    type: str = "object"                       # JSON type: object, array, string, null, integer, etc.
    description: str = ""
    fields: list["Action"] = field(default_factory=list)
    required: bool = False
    items: "Action | None" = None              # element type when type == "array"
    one_of: bool = False                       # exactly one of `fields` must be present


