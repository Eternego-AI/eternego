"""Request models — Pydantic schemas for validating incoming request bodies."""

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]


class PersonaCreateRequest(BaseModel):
    name: str
    thinking_model: str
    thinking_url: str
    thinking_provider: str | None = None
    thinking_api_key: str | None = None
    vision_model: str | None = None
    vision_url: str | None = None
    vision_provider: str | None = None
    vision_api_key: str | None = None
    frontier_model: str | None = None
    frontier_url: str | None = None
    frontier_provider: str | None = None
    frontier_api_key: str | None = None
    telegram_token: str | None = None
    discord_token: str | None = None


class PersonaControlRequest(BaseModel):
    entry_ids: list[str]


class HearRequest(BaseModel):
    message: str


class PairRequest(BaseModel):
    code: str
