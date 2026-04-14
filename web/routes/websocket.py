"""WebSocket route — /ws/{persona_id} streams chat and signals for a persona."""

from fastapi import APIRouter, WebSocket

from application.business import persona
from application.core.data import Channel
from application.platform import logger
from web.socket import manager, WebChannel

router = APIRouter()


@router.websocket("/ws/system")
async def system_websocket(ws: WebSocket):
    await manager.connect("__system__", ws)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception as e:
        logger.warning("System WebSocket error", {"error": str(e), "type": type(e).__name__})
    finally:
        manager.disconnect("__system__", ws)


@router.websocket("/ws/{persona_id}")
async def websocket_endpoint(persona_id: str, ws: WebSocket):
    await manager.connect(persona_id, ws)
    find_result = await persona.find(persona_id)
    live = None
    if find_result.success and find_result.data:
        loaded = await persona.loaded(find_result.data.persona)
        if loaded.success and loaded.data:
            live = loaded.data.persona
    channel = Channel(type="web", name=persona_id, bus=WebChannel(persona_id))
    if live:
        await persona.connect(live, channel)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception as e:
        logger.warning("WebSocket session error", {"error": str(e), "type": type(e).__name__})
    finally:
        manager.disconnect(persona_id, ws)
        if not manager.has_connections(persona_id) and live:
            await persona.disconnect(live, channel)
