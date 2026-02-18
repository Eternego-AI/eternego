"""Pages — server-rendered HTML routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from application.business import persona

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


_SECTIONS = {
    "person":  {"label": "Person",  "desc": "What the persona knows about you"},
    "traits":  {"label": "Traits",  "desc": "How the persona perceives you"},
    "agent":   {"label": "Agent",   "desc": "The persona's own identity and context"},
    "skills":  {"label": "Skills",  "desc": "Equipped skills and documents"},
    "history": {"label": "History", "desc": "Conversation history entries"},
}


@router.get("/dashboard")
async def dashboard(request: Request):
    outcome = await persona.agents()
    personas_list = (outcome.data or {}).get("personas", []) if outcome.success else []
    return templates.TemplateResponse("pages/dashboard.html", {
        "request": request,
        "personas": personas_list,
    })


@router.get("/dashboard/persona/{persona_id}/chat")
async def persona_chat(request: Request, persona_id: str):
    find = await persona.find(persona_id)
    if not find.success:
        return templates.TemplateResponse("pages/dashboard.html", {
            "request": request,
            "personas": [],
        }, status_code=404)
    return templates.TemplateResponse("pages/chat.html", {
        "request": request,
        "persona": find.data["persona"],
    })


@router.get("/dashboard/persona/{persona_id}")
async def persona_detail(request: Request, persona_id: str):
    find = await persona.find(persona_id)
    if not find.success:
        return templates.TemplateResponse("pages/dashboard.html", {
            "request": request,
            "personas": [],
            "error": find.message,
        }, status_code=404)

    found = find.data["persona"]
    oversee = await persona.oversee(found)
    sections = oversee.data if oversee.success else {}

    return templates.TemplateResponse("pages/persona.html", {
        "request": request,
        "persona": found,
        "sections": sections,
        "section_meta": _SECTIONS,
    })
