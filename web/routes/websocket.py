"""WebSocket route — /ws/{persona_id} streams chat and signals for a persona."""

from fastapi import APIRouter, WebSocket

from application.business import persona
from application.core.data import Channel
from application.platform import logger
from web.socket import manager, WebChannel

router = APIRouter()


@router.websocket("/ws/{persona_id}")
async def websocket_endpoint(persona_id: str, ws: WebSocket):
    await manager.connect(persona_id, ws)
    find = await persona.loaded(persona_id)
    channel = Channel(type="web", name=persona_id, bus=WebChannel(persona_id))
    if find.success:
        await persona.connect(find.data["persona"], channel)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception as e:
        logger.warning("WebSocket session error", {"error": str(e), "type": type(e).__name__})
    finally:
        manager.disconnect(persona_id, ws)
        if not manager.has_connections(persona_id) and find.success:
            await persona.disconnect(find.data["persona"], channel)
