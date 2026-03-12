"""OpenAI-compatible routes — /v1/models and /v1/chat/completions."""

from fastapi import APIRouter, HTTPException

from application.business import persona
from web.requests import ChatRequest

router = APIRouter()


# ── models ────────────────────────────────────────────────────────────────────

@router.get("/v1/models")
async def list_models():
    outcome = await persona.agents()
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)

    personas = (outcome.data or {}).get("personas", [])
    return {
        "object": "list",
        "data": [{"id": p.id, "object": "model", "owned_by": "eternego"} for p in personas],
    }


@router.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    outcome = await persona.find(model_id)
    if not outcome.success:
        raise HTTPException(status_code=404, detail=outcome.message)

    p = outcome.data["persona"]
    return {"id": p.id, "object": "model", "owned_by": "eternego"}


# ── chat completions ──────────────────────────────────────────────────────────

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    import asyncio

    outcome = await persona.loaded(request.model)
    if not outcome.success:
        raise HTTPException(status_code=404, detail=outcome.message)

    live = outcome.data["persona"]

    user_messages = [msg for msg in request.messages if msg.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message in request.")

    from application.core.data import Channel, Message
    channel = Channel(type="completion", name=request.model, bus=asyncio.Queue())
    message = Message(channel=channel, content=user_messages[-1].content)

    from config import web as web_config
    outcome = await persona.query(live, message, timeout=web_config.CHAT_TIMEOUT)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)

    return {
        "object": "chat.completion",
        "model": live.id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": outcome.data.get("response", "")},
                "finish_reason": "stop",
            }
        ],
    }
