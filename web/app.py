"""Web application — FastAPI app with OpenAI-compatible API and dashboard."""

import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from application.platform import logger
from application.platform.observer import Command, Plan, subscribe
from web.routes import api, openai, pages, websocket
from web.state import active_threads

app = FastAPI(title="Eternego", docs_url=None, redoc_url=None)

app.include_router(openai.router)
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(websocket.router)


def _on_reasoning_plan(signal: Plan) -> Command | None:
    if signal.title not in ("Reasoning", "Chaining"):
        return None
    thread = signal.details.get("thread")
    channel = signal.details.get("channel")
    if thread and channel and channel.type == "web" and thread.id not in active_threads:
        return Command("Stop Reasoning", {"thread": thread})
    return None


subscribe(_on_reasoning_plan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", {
        "path": str(request.url),
        "method": request.method,
        "error": str(exc),
        "type": type(exc).__name__,
        "trace": traceback.format_exc(),
    })
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})
