"""Agent routes — dynamic per-agent endpoints registered when an agent starts.

Each handler closes over the agent and passes its persona to specs.
The persona carries its own ego (dynamic attribute) for specs that need it.
"""

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.routing import Route

from application.business import persona as persona_spec
from application.core.data import Channel, Message
from web.requests import HearRequest, PersonaControlRequest


def register_routes(app: FastAPI, agent) -> None:
    """Register persona-specific routes for a running agent."""
    p = agent.persona
    prefix = f"/api/persona/{p.id}"

    async def get_mind():
        outcome = await persona_spec.mind(p)
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=404, detail=outcome.message)
        return outcome.data

    async def oversee():
        outcome = await persona_spec.oversee(p)
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        return outcome.data

    async def get_conversation():
        outcome = await persona_spec.conversation(p)
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=404, detail=outcome.message)
        return outcome.data

    async def control(request: PersonaControlRequest):
        outcome = await persona_spec.control(p, request.entry_ids)
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        return outcome.data

    async def sleep():
        outcome = await agent.sleep()
        if not outcome.success:
            raise HTTPException(status_code=400, detail=outcome.message)
        # Restart handled by manager's on_persona_asleep signal handler
        return outcome.data

    async def hear(request: HearRequest):
        channel = Channel(type="web", name=p.id)
        message = Message(channel=channel, content=request.message)
        outcome = await persona_spec.hear(p, message)
        if not outcome.success:
            raise HTTPException(status_code=500, detail=outcome.message)
        return {"status": "received"}

    async def feed(
        history: UploadFile = File(...),
        source: str = Form(...),
    ):
        data = (await history.read()).decode("utf-8")
        outcome = await persona_spec.feed(p, data, source)
        if not outcome.success or not outcome.data:
            raise HTTPException(status_code=400, detail=outcome.message)
        return outcome.data

    app.add_api_route(f"{prefix}/mind", get_mind, methods=["GET"])
    app.add_api_route(f"{prefix}/oversee", oversee, methods=["GET"])
    app.add_api_route(f"{prefix}/conversation", get_conversation, methods=["GET"])
    app.add_api_route(f"{prefix}/control", control, methods=["POST"])
    app.add_api_route(f"{prefix}/sleep", sleep, methods=["POST"])
    app.add_api_route(f"{prefix}/hear", hear, methods=["POST"])
    app.add_api_route(f"{prefix}/feed", feed, methods=["POST"])


def unregister_routes(app: FastAPI, persona_id: str) -> None:
    """Remove all dynamic routes for a persona."""
    prefix = f"/api/persona/{persona_id}/"
    app.router.routes[:] = [
        r for r in app.router.routes
        if not (isinstance(r, Route) and getattr(r, "path", "").startswith(prefix))
    ]
