"""Pages — serves the OS UI.

The single-page app owns its own routing. Any non-API, non-static path
serves index.html and lets the SPA decide what to render.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_INDEX = Path(__file__).parent.parent / "ui" / "index.html"


@router.get("/")
async def root():
    return FileResponse(_INDEX)


@router.get("/{full_path:path}")
async def spa(full_path: str):
    """Catch-all for SPA paths (/persona/{id}, /setup, /persona/{id}/inner, …).

    API and static paths are matched by their own routers/mounts before this
    one runs, so reaching here means the URL is meant for the SPA.
    """
    return FileResponse(_INDEX)
