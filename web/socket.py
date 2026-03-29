"""WebSocket connection manager and signal subscriber."""

import json

from fastapi import WebSocket

from application.platform import logger, objects
from application.platform.observer import Signal


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, persona_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(persona_id, []).append(ws)

    def disconnect(self, persona_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(persona_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(persona_id, None)

    def has_connections(self, persona_id: str) -> bool:
        return bool(self._connections.get(persona_id))

    async def broadcast(self, persona_id: str, data: str) -> None:
        for ws in list(self._connections.get(persona_id, [])):
            try:
                await ws.send_text(data)
            except Exception as e:
                logger.warning("WebSocket broadcast failed", {"error": str(e), "type": type(e).__name__})
                conns = self._connections.get(persona_id, [])
                if ws in conns:
                    conns.remove(ws)

    async def broadcast_all(self, data: str) -> None:
        for persona_id in list(self._connections):
            await self.broadcast(persona_id, data)


class WebChannel:
    """Broadcast-only bus for web channels — no queue, just sends to WebSocket clients."""

    def __init__(self, persona_id: str):
        self._persona_id = persona_id

    async def put(self, text: str) -> None:
        data = json.dumps({
            "type": "chat_message",
            "persona_id": self._persona_id,
            "content": text,
        })
        await manager.broadcast(self._persona_id, data)


manager = ConnectionManager()


async def on_signal(signal: Signal) -> None:
    """Forward every bus signal to all connected WebSocket clients."""
    if not manager._connections:
        return
    data = json.dumps({
        "type": signal.__class__.__name__,
        "title": signal.title,
        "time": signal.time,
        "details": objects.safe(signal.details),
    })
    await manager.broadcast_all(data)
