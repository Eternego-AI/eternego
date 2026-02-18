"""Internal API routes — Eternego-specific endpoints."""

from fastapi import APIRouter, HTTPException

from application.business import persona
from web.requests import PersonaControlRequest, PersonaCreateRequest, PersonaMigrateRequest

router = APIRouter(prefix="/api")


@router.post("/persona/create")
async def create_persona(request: PersonaCreateRequest):
    outcome = await persona.create(
        name=request.name,
        model=request.model,
        channel_name=request.channel_name,
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
