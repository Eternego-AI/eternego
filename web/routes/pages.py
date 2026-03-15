"""Pages — serves the OS UI."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/")
async def root():
    return FileResponse(Path(__file__).parent.parent / "os" / "index.html")
