"""WebSocket connection manager for system-wide bus signal forwarding.

Per-persona chat delivery goes through the persona's web Connection
(application/platform/web.py) — this module only handles the cross-persona
signal broadcast that the UI subscribes to for live status updates.
"""

import json

from fastapi import WebSocket

from application.platform import logger, objects
from application.platform.observer import Signal


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, key: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(key, []).append(ws)

    def disconnect(self, key: str, ws: WebSocket) -> None:
        conns = self._connections.get(key, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(key, None)

    async def broadcast_all(self, data: str) -> None:
        for key in list(self._connections):
            for ws in list(self._connections.get(key, [])):
                try:
                    await ws.send_text(data)
                except Exception as e:
                    logger.warning("WebSocket broadcast failed", {"error": str(e), "type": type(e).__name__})
                    conns = self._connections.get(key, [])
                    if ws in conns:
                        conns.remove(ws)


manager = ConnectionManager()


async def on_signal(signal: Signal) -> None:
    """Forward every bus signal to all connected WebSocket clients — system WS
    and all per-persona WSs alike. This is the debug/status feed the UI uses."""
    if not manager._connections:
        return
    data = json.dumps({
        "type": signal.__class__.__name__,
        "title": signal.title,
        "time": signal.time,
        "details": objects.safe(signal.details),
    })
    await manager.broadcast_all(data)
