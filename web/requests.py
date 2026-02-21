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
    model: str
    network_type: str
    network_credentials: dict
    frontier_model: str | None = None
    frontier_provider: str | None = None
    frontier_credentials: dict | None = None


class PersonaMigrateRequest(BaseModel):
    diary_path: str
    phrase: str
    model: str


class PersonaControlRequest(BaseModel):
    entry_ids: list[str]
