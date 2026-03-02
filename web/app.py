"""Web application — FastAPI app with OpenAI-compatible API and dashboard."""

import traceback

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from application.platform import logger
from web.routes import api, openai, pages, websocket

app = FastAPI(title="Eternego", docs_url=None, redoc_url=None)

app.mount("/assets", StaticFiles(directory=Path(__file__).parent.parent / "assets"), name="assets")

app.include_router(openai.router)
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(websocket.router)


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
