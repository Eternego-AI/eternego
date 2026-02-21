"""WebSocket route — /ws streams all bus signals to connected clients."""

from fastapi import APIRouter, WebSocket

from application.platform import logger
from web.socket import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception as e:
        logger.warning("WebSocket session error", {"error": str(e), "type": type(e).__name__})
    finally:
        manager.disconnect(ws)
