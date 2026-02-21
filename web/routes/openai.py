"""OpenAI-compatible routes — /v1/models and /v1/chat/completions."""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from application.business import persona
from application.core.data import Channel, Message
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
    outcome = await persona.find(request.model)
    if not outcome.success:
        raise HTTPException(status_code=404, detail=outcome.message)

    found = outcome.data["persona"]

    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message in request.")

    channel = Channel(type="web", name=str(uuid.uuid4()))
    future = asyncio.get_running_loop().create_future()
    outcome = await persona.connect(
        found, channel,
        on_send=lambda text, _f=future: _f.set_result(text) if not _f.done() else None,
        on_wait=lambda _f=future: _f,
    )
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)

    gw = outcome.data["gateway"]
    await persona.hear(found, Message(channel=channel, content=user_messages[-1].content))

    try:
        response = await asyncio.wait_for(gw.wait(), timeout=120)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Persona did not respond in time.")
    finally:
        await persona.disconnect(found, channel)

    return {
        "object": "chat.completion",
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response},
                "finish_reason": "stop",
            }
        ],
    }
