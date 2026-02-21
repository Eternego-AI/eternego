"""WebSocket connection manager and signal subscriber."""

import json

from fastapi import WebSocket

from application.platform import logger, objects
from application.platform.observer import Signal


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, data: str) -> None:
        for ws in list(self._connections):
            try:
                await ws.send_text(data)
            except Exception as e:
                logger.warning("WebSocket broadcast failed", {"error": str(e), "type": type(e).__name__})
                self._connections.remove(ws)


manager = ConnectionManager()


async def on_signal(signal: Signal) -> None:
    """Forward every bus signal to all connected WebSocket clients."""
    if not manager._connections:
        return
    data = json.dumps({
        "type": signal.__class__.__name__,
        "title": signal.title,
        "details": objects.safe(signal.details),
    })
    await manager.broadcast(data)
