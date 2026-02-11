"""Data models for the application."""

from dataclasses import dataclass


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
