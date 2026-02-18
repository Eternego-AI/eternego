"""Web application — FastAPI app with OpenAI-compatible API and dashboard."""

from fastapi import FastAPI

from web.routes import api, openai, pages, websocket

app = FastAPI(title="Eternego", docs_url=None, redoc_url=None)

app.include_router(openai.router)
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(websocket.router)
