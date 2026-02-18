"""Pages — server-rendered HTML routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from application.business import persona

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/dashboard")
async def dashboard(request: Request):
    outcome = await persona.agents()
    personas_list = (outcome.data or {}).get("personas", []) if outcome.success else []
    return templates.TemplateResponse("pages/dashboard.html", {
        "request": request,
        "personas": personas_list,
    })
