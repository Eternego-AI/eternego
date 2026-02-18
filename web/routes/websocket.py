"""WebSocket route — /ws streams all bus signals to connected clients."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from web.socket import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
