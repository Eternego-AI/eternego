"""Internal API routes — static and manager endpoints.

Static routes handle general operations (list, create, config).
Manager routes handle agent lifecycle (start, stop, restart, delete, export).
Per-agent routes (hear, mind, oversee, etc.) are registered dynamically
via web/routes/agent_routes.py when an agent is prepared.
"""

import tempfile

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from datetime import timedelta

from application.business import environment, persona
from application.platform import datetimes
import manager
from web.requests import EnvironmentPrepareRequest, PersonaCreateRequest

router = APIRouter(prefix="/api")


# ── Static routes ─────────────────────────────────────────────────────────────

@router.get("/config/providers")
async def get_provider_config():
    import config.inference as cfg
    return {
        "local": {"url": cfg.OLLAMA_BASE_URL},
        "anthropic": {"url": cfg.ANTHROPIC_BASE_URL},
        "openai": {"url": cfg.OPENAI_BASE_URL},
    }


@router.get("/personas")
async def list_personas():
    outcome = await persona.get_list()
    personas_list = outcome.data.personas if outcome.data else []
    return {"personas": [{"id": p.id, "name": p.name} for p in personas_list]}


@router.post("/environment/prepare")
async def prepare_environment(request: EnvironmentPrepareRequest):
    outcome = await environment.prepare(
        url=request.url,
        model=request.model or None,
        provider=request.provider,
        api_key=request.api_key,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data




@router.post("/persona/create")
async def create_persona(request: PersonaCreateRequest):
    outcome = await environment.prepare(
        url=request.thinking_url,
        model=request.thinking_model,
        provider=request.thinking_provider,
        api_key=request.thinking_api_key,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    thinking = outcome.data.model

    vision = None
    if request.vision_model:
        outcome = await environment.prepare(
            url=request.vision_url,
            model=request.vision_model,
            provider=request.vision_provider,
            api_key=request.vision_api_key,
        )
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        vision = outcome.data.model

    frontier = None
    if request.frontier_model:
        outcome = await environment.prepare(
            url=request.frontier_url,
            model=request.frontier_model,
            provider=request.frontier_provider,
            api_key=request.frontier_api_key,
        )
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        frontier = outcome.data.model

    outcome = await environment.check_channel(request.channel_type, request.channel_credentials)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    channel = outcome.data.channel

    outcome = await persona.create(
        name=request.name,
        thinking=thinking,
        channel=channel,
        vision=vision,
        frontier=frontier,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)

    try:
        manager.serve(outcome.data.persona)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona created but failed to start: {e}")

    return outcome.data


@router.post("/persona/migrate")
async def migrate_persona(
    diary: UploadFile = File(...),
    phrase: str = Form(...),
    model: str = Form(...),
    provider: str = Form(None),
    api_key: str = Form(None),
    url: str = Form(None),
    vision_model: str = Form(None),
    vision_provider: str = Form(None),
    vision_api_key: str = Form(None),
    vision_url: str = Form(None),
    frontier_model: str = Form(None),
    frontier_provider: str = Form(None),
    frontier_api_key: str = Form(None),
    frontier_url: str = Form(None),
):
    filename = diary.filename or "diary"
    tmp_dir = tempfile.mkdtemp()
    tmp_path = f"{tmp_dir}/{filename}"
    with open(tmp_path, "wb") as f:
        f.write(await diary.read())

    outcome = await environment.prepare(
        url=url,
        model=model,
        provider=provider or None,
        api_key=api_key,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    thinking = outcome.data.model

    vision = None
    if vision_model:
        outcome = await environment.prepare(
            url=vision_url,
            model=vision_model,
            provider=vision_provider or None,
            api_key=vision_api_key,
        )
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        vision = outcome.data.model

    frontier = None
    if frontier_model:
        outcome = await environment.prepare(
            url=frontier_url,
            model=frontier_model,
            provider=frontier_provider or None,
            api_key=frontier_api_key,
        )
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        frontier = outcome.data.model

    outcome = await persona.migrate(
        diary_path=tmp_path,
        phrase=phrase,
        thinking=thinking,
        vision=vision,
        frontier=frontier,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)

    try:
        manager.serve(outcome.data.persona)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona migrated but failed to start: {e}")

    return outcome.data


@router.get("/persona/{persona_id}")
async def get_persona(persona_id: str):
    find = await persona.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)
    p = find.data.persona
    running = manager.find_or_none(persona_id) is not None
    return {
        "id": p.id,
        "name": p.name,
        "base_model": p.base_model,
        "model": p.thinking.name if p.thinking else "",
        "birthday": p.birthday or "",
        "running": running,
        "channels": [
            {
                "type": ch.type,
                "name": ch.name,
                "verified": ch.verified_at is not None,
            }
            for ch in (p.channels or [])
        ],
    }


# ── Manager operation routes ──────────────────────────────────────────────────

@router.post("/persona/{persona_id}/start")
async def start_persona(persona_id: str):
    if manager.find_or_none(persona_id):
        return {"status": "already running"}

    find = await persona.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)

    try:
        manager.serve(find.data.persona)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "started"}


@router.post("/persona/{persona_id}/stop")
async def stop_persona(persona_id: str):
    if not manager.find_or_none(persona_id):
        raise HTTPException(status_code=404, detail="Persona is not running.")

    await manager.release(persona_id)
    return {"status": "stopped"}


@router.post("/persona/{persona_id}/restart")
async def restart_persona(persona_id: str):
    if manager.find_or_none(persona_id):
        await manager.restart(persona_id)
    else:
        find = await persona.find(persona_id)
        if not find.success or not find.data:
            raise HTTPException(status_code=404, detail=find.message)
        try:
            manager.serve(find.data.persona)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"status": "restarted"}


@router.post("/persona/{persona_id}/export")
async def export_persona(persona_id: str):
    find = await persona.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)

    if manager.find_or_none(persona_id):
        raise HTTPException(status_code=400, detail="Persona must be stopped before exporting. Stop it first.")

    outcome = await persona.export(find.data.persona)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)

    diary_path = Path(outcome.data.diary_path)
    return FileResponse(
        path=diary_path,
        filename=diary_path.name,
        media_type="application/octet-stream",
    )


@router.post("/persona/{persona_id}/delete")
async def delete_persona(persona_id: str):
    find = await persona.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)

    if manager.find_or_none(persona_id):
        await manager.release(persona_id)

    outcome = await persona.delete(find.data.persona)
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data
