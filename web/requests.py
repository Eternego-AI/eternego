"""Request models — Pydantic schemas for validating incoming request bodies."""

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]


class EnvironmentPrepareRequest(BaseModel):
    url: str | None = None
    model: str = ""
    provider: str | None = None
    api_key: str | None = None


class PersonaCreateRequest(BaseModel):
    name: str
    thinking_model: str
    thinking_url: str
    thinking_provider: str | None = None
    thinking_api_key: str | None = None
    channel_type: str
    channel_credentials: dict
    frontier_model: str | None = None
    frontier_url: str | None = None
    frontier_provider: str | None = None
    frontier_api_key: str | None = None


class PersonaControlRequest(BaseModel):
    entry_ids: list[str]


class HearRequest(BaseModel):
    message: str
