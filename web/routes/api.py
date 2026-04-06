"""Internal API routes — Eternego-specific endpoints."""

import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

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
    outcome = await environment.prepare(request.model or None)
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
async def migrate_persona(
    diary: UploadFile = File(...),
    phrase: str = Form(...),
    model: str = Form(...),
):
    filename = diary.filename or "diary"
    tmp_dir = tempfile.mkdtemp()
    tmp_path = f"{tmp_dir}/{filename}"
    with open(tmp_path, "wb") as f:
        f.write(await diary.read())

    outcome = await persona.migrate(
        diary_path=tmp_path,
        phrase=phrase,
        model=model,
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
        "model": p.model.name if p.model else "",
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
