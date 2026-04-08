"""Internal API routes — Eternego-specific endpoints."""

import tempfile

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from application.business import environment, persona
from web.requests import EnvironmentPrepareRequest, HearRequest, PersonaControlRequest, PersonaCreateRequest

router = APIRouter(prefix="/api")


@router.get("/personas")
async def list_personas():
    outcome = await persona.get_list()
    personas_list = (outcome.data or {}).get("personas", []) if outcome.success else []
    return {"personas": [{"id": p.id, "name": p.name} for p in personas_list]}



@router.post("/environment/prepare")
async def prepare_environment(request: EnvironmentPrepareRequest):
    outcome = await environment.prepare(
        model=request.model or None,
        provider=request.provider,
        credentials=request.credentials,
    )
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/pair/{code}")
async def pair_channel(code: str):
    outcome = await environment.pair(code)
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/create")
async def create_persona(request: PersonaCreateRequest):
    from application.core.data import Model, Channel

    thinking = Model(
        name=request.thinking_model,
        provider=request.thinking_provider,
        credentials=request.thinking_credentials,
    )
    outcome = await environment.prepare(
        model=thinking.name,
        provider=thinking.provider,
        credentials=(thinking.credentials or {}).get("api_key"),
    )
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)

    frontier = None
    if request.frontier_model:
        frontier = Model(
            name=request.frontier_model,
            provider=request.frontier_provider,
            credentials=request.frontier_credentials,
        )
        outcome = await environment.prepare(
            model=frontier.name,
            provider=frontier.provider,
            credentials=(frontier.credentials or {}).get("api_key"),
        )
        if not outcome.success:
            raise HTTPException(status_code=400, detail=outcome.message)

    channel = Channel(type=request.channel_type, credentials=request.channel_credentials)

    if request.channel_type == "telegram":
        outcome = await environment.check_channel(request.channel_type, request.channel_credentials)
        if not outcome.success:
            raise HTTPException(status_code=400, detail=outcome.message)

    outcome = await persona.create(
        name=request.name,
        thinking=thinking,
        channel=channel,
        frontier=frontier,
    )
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/migrate")
async def migrate_persona(
    diary: UploadFile = File(...),
    phrase: str = Form(...),
    model: str = Form(...),
    provider: str = Form(None),
    credentials: str = Form(None),
):
    from application.core.data import Model

    filename = diary.filename or "diary"
    tmp_dir = tempfile.mkdtemp()
    tmp_path = f"{tmp_dir}/{filename}"
    with open(tmp_path, "wb") as f:
        f.write(await diary.read())

    creds = {"api_key": credentials} if credentials else None
    thinking = Model(name=model, provider=provider or None, credentials=creds)

    outcome = await environment.prepare(
        model=thinking.name,
        provider=thinking.provider,
        credentials=(thinking.credentials or {}).get("api_key"),
    )
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)

    outcome = await persona.migrate(
        diary_path=tmp_path,
        phrase=phrase,
        thinking=thinking,
    )
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.get("/persona/{persona_id}")
async def get_persona(persona_id: str):
    find = await persona.find(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    p = find.data["persona"]
    return {
        "id": p.id,
        "name": p.name,
        "base_model": p.base_model,
        "model": p.thinking.name if p.thinking else "",
        "birthday": p.birthday or "",
        "channels": [
            {
                "type": ch.type,
                "name": ch.name,
                "verified": ch.verified_at is not None,
            }
            for ch in (p.channels or [])
        ],
    }


@router.get("/persona/{persona_id}/mind")
async def get_mind(persona_id: str):
    outcome = await persona.mind(persona_id)
    if not outcome.success:
        raise HTTPException(status_code=404, detail=outcome.message)
    return outcome.data


@router.get("/persona/{persona_id}/oversee")
async def oversee_persona(persona_id: str):
    find = await persona.loaded(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona.oversee(find.data["persona"])
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.get("/persona/{persona_id}/conversation")
async def get_conversation(persona_id: str):
    outcome = await persona.conversation(persona_id)
    if not outcome.success:
        raise HTTPException(status_code=404, detail=outcome.message)
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


@router.post("/persona/{persona_id}/stop")
async def stop_persona(persona_id: str):
    find = await persona.loaded(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona.nap(find.data["persona"])
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/start")
async def start_persona(persona_id: str):
    """Wake a stopped persona."""
    from application.platform.asyncio_worker import Worker
    # If already running, just return success
    loaded_check = await persona.loaded(persona_id)
    if loaded_check.success:
        return {"status": "already running"}
    outcome = await persona.wake(persona_id, Worker())
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/restart")
async def restart_persona(persona_id: str):
    from application.platform.asyncio_worker import Worker
    # Stop if running
    loaded_check = await persona.loaded(persona_id)
    if loaded_check.success:
        await persona.nap(loaded_check.data["persona"])
    # Wake
    outcome = await persona.wake(persona_id, Worker())
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/export")
async def export_persona(persona_id: str):
    """Export a stopped persona's diary for download."""
    loaded_check = await persona.loaded(persona_id)
    if loaded_check.success:
        raise HTTPException(status_code=400, detail="Persona must be stopped before exporting. Stop it first.")

    outcome = await persona.export(persona_id)
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)

    diary_path = Path(outcome.data["diary_path"])
    return FileResponse(
        path=diary_path,
        filename=diary_path.name,
        media_type="application/octet-stream",
    )


@router.post("/persona/{persona_id}/delete")
async def delete_persona(persona_id: str):
    loaded = await persona.loaded(persona_id)
    if loaded.success:
        await persona.nap(loaded.data["persona"])
    find = await persona.find(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona.delete(find.data["persona"])
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/feed")
async def feed_persona(
    persona_id: str,
    history: UploadFile = File(...),
    source: str = Form(...),
):
    find = await persona.loaded(persona_id)
    if not find.success:
        raise HTTPException(status_code=404, detail=find.message)
    data = (await history.read()).decode("utf-8")
    outcome = await persona.feed(find.data["persona"], data, source)
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
    channel = Channel(type="web", name=persona_id)
    message = Message(channel=channel, content=request.message)
    outcome = await persona.hear(live, message)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)
    return {"status": "received"}
