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
from web import health as health_view
from web.requests import PersonaCreateRequest, HearRequest, PersonaControlRequest, PairRequest


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
    return {"personas": [_persona_view(p) for p in personas_list]}


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

    channels = []
    if request.telegram_token:
        try:
            channels.append(await manager.validate_channel("telegram", {"token": request.telegram_token}))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Telegram validation failed: {e}")
    if request.discord_token:
        try:
            channels.append(await manager.validate_channel("discord", {"token": request.discord_token}))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Discord validation failed: {e}")

    outcome = await persona_spec.create(
        name=request.name,
        thinking=thinking,
        channels=channels,
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
    telegram_token: str = Form(None),
    discord_token: str = Form(None),
):
    filename = diary.filename or "diary"
    tmp_dir = tempfile.mkdtemp()
    tmp_path = f"{tmp_dir}/{filename}"
    with open(tmp_path, "wb") as f:
        f.write(await diary.read())

    outcome = await environment.prepare(
        url=url,
        model=model,
        provider=provider,
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
            provider=vision_provider,
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
            provider=frontier_provider,
            api_key=frontier_api_key,
        )
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        frontier = outcome.data.model

    channels = []
    if telegram_token:
        try:
            channels.append(await manager.validate_channel("telegram", {"token": telegram_token}))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Telegram validation failed: {e}")
    if discord_token:
        try:
            channels.append(await manager.validate_channel("discord", {"token": discord_token}))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Discord validation failed: {e}")

    outcome = await persona_spec.migrate(
        diary_path=tmp_path,
        phrase=phrase,
        thinking=thinking,
        vision=vision,
        frontier=frontier,
        channels=channels,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)

    try:
        await manager.add(outcome.data.persona)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona migrated but failed to start: {e}")

    return outcome.data


# ── Persona config routes (available whether active or not) ──────────────────

def _model_view(model):
    if model is None:
        return None
    return {"name": model.name, "provider": model.provider, "url": model.url}


def _thinking_view(p):
    if p.thinking is None:
        return None
    # For local thinking, the wrapped name (eternego-<id>) is internal —
    # surface the human-readable base model name instead.
    name = p.base_model or p.thinking.name
    return {"name": name, "provider": p.thinking.provider, "url": p.thinking.url}


def _persona_view(p):
    return {
        "id": p.id,
        "name": p.name,
        "base_model": p.base_model,
        "birthday": p.birthday or "",
        "running": manager.find(p.id) is not None,
        "status": p.status,
        "thinking": _thinking_view(p),
        "vision": _model_view(p.vision),
        "frontier": _model_view(p.frontier),
        "channels": [
            {
                "type": ch.type,
                "name": ch.name,
                "verified": ch.verified_at is not None,
            }
            for ch in (p.channels or [])
        ],
    }


@router.get("/persona/{persona_id}/diagnose")
async def diagnose_persona(persona_id: str):
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)
    outcome = await persona_spec.diagnose(find.data.persona)
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)
    return {
        "status": outcome.data.status,
        "mind": outcome.data.mind,
        "uptime": health_view.uptime_grid(outcome.data.health),
    }


async def _validate_model(field):
    if not field:
        return None
    prep = await environment.prepare(
        url=field.get("url"),
        model=field.get("model"),
        provider=field.get("provider"),
        api_key=field.get("api_key"),
    )
    if not prep.success or not prep.data:
        raise HTTPException(status_code=400, detail=prep.message)
    return prep.data.model


@router.post("/persona/{persona_id}/update")
async def update_persona(persona_id: str, request: dict):
    find = await persona_spec.find(persona_id)
    if not find.success or not find.data:
        raise HTTPException(status_code=404, detail=find.message)

    clear_vision = bool(request.get("clear_vision"))
    clear_frontier = bool(request.get("clear_frontier"))
    thinking = await _validate_model(request.get("thinking"))
    vision = None if clear_vision else await _validate_model(request.get("vision"))
    frontier = None if clear_frontier else await _validate_model(request.get("frontier"))

    outcome = await persona_spec.update(
        find.data.persona,
        status=request.get("status"),
        thinking=thinking,
        vision=vision,
        frontier=frontier,
        clear_vision=clear_vision,
        clear_frontier=clear_frontier,
    )
    if not outcome.success or not outcome.data:
        raise HTTPException(status_code=400, detail=outcome.message)

    persona = outcome.data.persona
    is_running = manager.find(persona_id) is not None
    models_changed = thinking is not None or vision is not None or frontier is not None or clear_vision or clear_frontier

    try:
        if persona.status == "active":
            if is_running:
                await manager.restart(persona_id)
            else:
                await manager.add(persona)
        elif persona.status in ("hibernate", "sick"):
            if is_running:
                await manager.remove(persona_id)
        elif models_changed and is_running:
            await manager.restart(persona_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Updated but lifecycle change failed: {e}")

    return {"status": persona.status, "running": manager.find(persona_id) is not None}


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
    gw = next((g for g in agent.gateways if g["channel"].type == "web"), None)
    if gw is None:
        raise HTTPException(status_code=400, detail="Web channel not connected")
    gw["connection"].dispatch_message(persona_id, request.message)
    return {"status": "received"}


@router.post("/persona/{persona_id}/see")
async def see_persona(persona_id: str, image: UploadFile = File(...), caption: str = Form("")):
    agent = _require_agent(persona_id)
    gw = next((g for g in agent.gateways if g["channel"].type == "web"), None)
    if gw is None:
        raise HTTPException(status_code=400, detail="Web channel not connected")
    suffix = Path(image.filename or "").suffix or ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await image.read())
    tmp.close()
    gw["connection"].dispatch_media(persona_id, tmp.name, caption or "")
    return {"status": "received"}


@router.post("/persona/{persona_id}/feed")
async def feed_persona(
    persona_id: str,
    history: UploadFile = File(...),
    source: str = Form(...),
):
    agent = _require_agent(persona_id)
    data = (await history.read()).decode("utf-8")
    outcome = await persona_spec.feed(agent.living, data, source)
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


@router.get("/persona/{persona_id}/export")
async def export_persona(persona_id: str):
    diary_file = paths.diary(persona_id) / f"{persona_id}.diary"
    if not diary_file.exists():
        raise HTTPException(
            status_code=404,
            detail="No diary file yet — wait until the persona's first nightly sleep.",
        )
    return FileResponse(
        path=diary_file,
        filename=diary_file.name,
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
