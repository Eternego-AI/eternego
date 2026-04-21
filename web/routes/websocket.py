"""WebSocket routes — /ws/{persona_id} streams chat and signals for a persona,
/ws/system streams system-wide bus signals."""

from fastapi import APIRouter, WebSocket

import manager
from application.core.data import Channel
from application.platform import logger
from web.socket import manager as ws_manager

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

    agent = manager.find(persona_id)
    web_gateway = None
    sender = None

    if agent:
        web_gateway = next(
            (g for g in agent.gateways if g.channel.type == "web"),
            None,
        )
        if web_gateway is None:
            await agent.connect(Channel(type="web", name=persona_id))
            web_gateway = next(
                (g for g in agent.gateways if g.channel.type == "web"),
                None,
            )

        if web_gateway is not None:
            async def send_to_ws(data: str) -> None:
                await ws.send_text(data)
            web_gateway.connection.subscribe(persona_id, send_to_ws)
            sender = send_to_ws

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception as e:
        logger.warning("WebSocket session error", {"error": str(e), "type": type(e).__name__})
    finally:
        if web_gateway and sender:
            web_gateway.connection.unsubscribe(persona_id, sender)
        ws_manager.disconnect(persona_id, ws)
