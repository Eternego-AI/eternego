"""WebSocket route — /ws/{persona_id} streams chat and signals for a persona."""

from fastapi import APIRouter, WebSocket

import manager
from application.core.data import Channel
from application.platform import logger
from web.socket import manager as ws_manager, WebChannel

router = APIRouter()


@router.websocket("/ws/system")
async def system_websocket(ws: WebSocket):
    await ws_manager.connect("__system__", ws)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception as e:
        logger.warning("System WebSocket error", {"error": str(e), "type": type(e).__name__})
    finally:
        ws_manager.disconnect("__system__", ws)


@router.websocket("/ws/{persona_id}")
async def websocket_endpoint(persona_id: str, ws: WebSocket):
    await ws_manager.connect(persona_id, ws)
    agent = manager.find_or_none(persona_id)
    channel = Channel(type="web", name=persona_id, bus=WebChannel(persona_id))
    if agent:
        await agent.connect(channel)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception as e:
        logger.warning("WebSocket session error", {"error": str(e), "type": type(e).__name__})
    finally:
        ws_manager.disconnect(persona_id, ws)
        if not ws_manager.has_connections(persona_id) and agent:
            await agent.disconnect(channel)
