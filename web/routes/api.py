"""Internal API routes — Eternego-specific endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from application.business import environment, persona
from web.requests import HearRequest, PersonaControlRequest, PersonaCreateRequest, PersonaMigrateRequest

router = APIRouter(prefix="/api")

_LOG_FILES = {
    "app":     Path("eternego.log"),
    "signals": Path("eternego-signals.log"),
}


@router.get("/logs")
async def get_logs(file: str = Query("app"), tail: int = Query(200)):
    path = _LOG_FILES.get(file)
    if path is None:
        raise HTTPException(status_code=400, detail="Unknown log file")
    if not path.exists():
        return {"entries": []}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    entries = []
    for line in lines[-tail:]:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            entries.append({"level": "info", "title": line, "time": "", "context": {}})
    return {"entries": entries}


@router.get("/models")
async def get_models():
    outcome = await environment.info()
    return outcome.data


@router.post("/pair/{code}")
async def pair_channel(code: str):
    outcome = await environment.pair(code)
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/create")
async def create_persona(request: PersonaCreateRequest):
    outcome = await persona.create(
        name=request.name,
        model=request.model,
        channel_type=request.channel_type,
        channel_credentials=request.channel_credentials,
        frontier_model=request.frontier_model,
        frontier_provider=request.frontier_provider,
        frontier_credentials=request.frontier_credentials,
    )
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/migrate")
async def migrate_persona(request: PersonaMigrateRequest):
    outcome = await persona.migrate(
        diary_path=request.diary_path,
        phrase=request.phrase,
        model=request.model,
    )
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/control")
async def control_persona(persona_id: str, request: PersonaControlRequest):
    find = await persona.find(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona.control(find.data["persona"], request.entry_ids)
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/sleep")
async def sleep_persona(persona_id: str):
    find = await persona.loaded(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona.sleep(find.data["persona"])
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/hear")
async def hear_persona(persona_id: str, request: HearRequest):
    find = await persona.loaded(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    live = find.data["persona"]

    from application.core.data import Channel, Message
    from web.socket import WebSocketBus
    channel = Channel(type="web", name=persona_id, bus=WebSocketBus(persona_id))
    message = Message(channel=channel, content=request.message)

    outcome = await persona.hear(live, message)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)
    return {"status": "received"}
