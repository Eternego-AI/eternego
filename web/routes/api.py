"""Internal API routes.

All per-persona routes are static with a `{persona_id}` path parameter. Routes
that need a live agent look it up via `manager.find(persona_id)` and
return 409 when the persona isn't being served. Routes that only touch
persisted config work whether the persona is active or not.
"""

import tempfile

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from application.business import environment, persona as persona_spec
from application.core import paths
import manager
from web.requests import EnvironmentPrepareRequest, PersonaCreateRequest, HearRequest, PersonaControlRequest, PairRequest


router = APIRouter(prefix="/api")


# ── Config and list routes ────────────────────────────────────────────────────

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
    outcome = await persona_spec.get_list()
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


# ── Create / Migrate ──────────────────────────────────────────────────────────

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

    try:
        channel = await manager.validate_channel(request.channel_type, request.channel_credentials)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Channel validation failed: {e}")

    outcome = await persona_spec.create(
        name=request.name,
        thinking=thinking,
        channel=channel,
        vision=vision,
        frontier=frontier,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)

    try:
        await manager.add(outcome.data.persona)
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

    outcome = await persona_spec.migrate(
        diary_path=tmp_path,
        phrase=phrase,
        thinking=thinking,
        vision=vision,
        frontier=frontier,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)

    try:
        await manager.add(outcome.data.persona)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona migrated but failed to start: {e}")

    return outcome.data


# ── Persona config routes (available whether active or not) ──────────────────

@router.get("/persona/{persona_id}")
async def get_persona(persona_id: str):
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)
    p = find.data.persona
    running = manager.find(persona_id) is not None
    return {
        "id": p.id,
        "name": p.name,
        "base_model": p.base_model,
        "model": p.thinking.name if p.thinking else "",
        "birthday": p.birthday or "",
        "running": running,
        "status": p.status,
        "channels": [
            {
                "type": ch.type,
                "name": ch.name,
                "verified": ch.verified_at is not None,
            }
            for ch in (p.channels or [])
        ],
    }


@router.get("/persona/{persona_id}/oversee")
async def oversee_persona(persona_id: str):
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona_spec.oversee(find.data.persona)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.get("/persona/{persona_id}/conversation")
async def get_conversation(persona_id: str):
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona_spec.conversation(find.data.persona)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=404, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/control")
async def control_persona(persona_id: str, request: PersonaControlRequest):
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona_spec.control(find.data.persona, request.entry_ids)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.get("/persona/{persona_id}/media/{filename}")
async def persona_media(persona_id: str, filename: str):
    media_dir = paths.media(persona_id).resolve()
    target = (media_dir / filename).resolve()
    if not str(target).startswith(str(media_dir)) or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path=target)


# ── Live-agent routes (require the persona to be served) ─────────────────────

def _require_agent(persona_id: str):
    agent = manager.find(persona_id)
    if agent is None:
        raise HTTPException(status_code=409, detail="Persona is not active.")
    return agent


@router.get("/persona/{persona_id}/mind")
async def get_mind(persona_id: str):
    agent = _require_agent(persona_id)
    outcome = await persona_spec.mind(agent.ego)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=404, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/sleep")
async def sleep_persona(persona_id: str):
    agent = _require_agent(persona_id)
    outcome = await agent.sleep()
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/hear")
async def hear_persona(persona_id: str, request: HearRequest):
    agent = _require_agent(persona_id)
    gw = next((g for g in agent.gateways if g.channel.type == "web"), None)
    outcome = await persona_spec.hear(agent.ego, content=request.message, gateway=gw)
    if not outcome.success:
        raise HTTPException(status_code=500, detail=outcome.message)
    return {"status": "received"}


@router.post("/persona/{persona_id}/see")
async def see_persona(persona_id: str, image: UploadFile = File(...), caption: str = Form("")):
    agent = _require_agent(persona_id)
    suffix = Path(image.filename or "").suffix or ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(await image.read())
        tmp.close()
        gw = next((g for g in agent.gateways if g.channel.type == "web"), None)
        saved = gw.save_media_copy(tmp.name) if gw else tmp.name
        outcome = await persona_spec.see(
            agent.ego,
            source=saved,
            caption=caption or "",
            gateway=gw,
        )
        if not outcome.success:
            raise HTTPException(status_code=500, detail=outcome.message)
        return {"status": "received"}
    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/persona/{persona_id}/feed")
async def feed_persona(
    persona_id: str,
    history: UploadFile = File(...),
    source: str = Form(...),
):
    agent = _require_agent(persona_id)
    data = (await history.read()).decode("utf-8")
    outcome = await persona_spec.feed(agent.ego, data, source)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


@router.post("/persona/{persona_id}/pair")
async def pair_persona(persona_id: str, request: PairRequest):
    agent = _require_agent(persona_id)
    outcome = await agent.pair(request.code)
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data


# ── Lifecycle routes ─────────────────────────────────────────────────────────

@router.post("/persona/{persona_id}/start")
async def start_persona(persona_id: str):
    if manager.find(persona_id):
        return {"status": "already running"}

    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)

    try:
        await manager.add(find.data.persona)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "started"}


@router.post("/persona/{persona_id}/stop")
async def stop_persona(persona_id: str):
    if not manager.find(persona_id):
        raise HTTPException(status_code=404, detail="Persona is not running.")

    await manager.remove(persona_id)
    return {"status": "stopped"}


@router.post("/persona/{persona_id}/restart")
async def restart_persona(persona_id: str):
    if manager.find(persona_id):
        await manager.restart(persona_id)
    else:
        find = await persona_spec.find(persona_id)
        if not find.success or not find.data:
            raise HTTPException(status_code=404, detail=find.message)
        try:
            await manager.add(find.data.persona)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"status": "restarted"}


@router.post("/persona/{persona_id}/export")
async def export_persona(persona_id: str):
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)

    if manager.find(persona_id):
        raise HTTPException(status_code=400, detail="Persona must be stopped before exporting. Stop it first.")

    outcome = await persona_spec.export(find.data.persona)
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
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)

    if manager.find(persona_id):
        await manager.remove(persona_id)

    outcome = await persona_spec.delete(find.data.persona)
    if not outcome.success:
        raise HTTPException(status_code=400, detail=outcome.message)
    return outcome.data
