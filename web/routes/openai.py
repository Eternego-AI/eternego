"""OpenAI-compatible routes — /v1/models and /v1/chat/completions."""

from fastapi import APIRouter, HTTPException

from application.business import persona
from web.requests import ChatRequest

router = APIRouter()


# ── models ────────────────────────────────────────────────────────────────────

@router.get("/v1/models")
async def list_models():
    outcome = await persona.get_list()
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)

    personas = outcome.data.personas if outcome.data else []
    return {
        "object": "list",
        "data": [{"id": p.id, "object": "model", "owned_by": "eternego"} for p in personas],
    }


@router.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    outcome = await persona.find(model_id)
    if not outcome.success:
        raise HTTPException(status_code=404, detail=outcome.message)

    p = outcome.data.persona
    return {"id": p.id, "object": "model", "owned_by": "eternego"}


# ── chat completions ──────────────────────────────────────────────────────────

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    find = await persona.find(request.model)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona.loaded(find.data.persona)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=404, detail=outcome.message)

    live = outcome.data.persona

    outcome = await persona.query(live, request.message)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)

    return {
        "object": "chat.completion",
        "model": live.id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": outcome.data.response if outcome.data else ""},
                "finish_reason": "stop",
            }
        ],
    }
