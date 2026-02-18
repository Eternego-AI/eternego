"""WebSocket connection manager and signal subscriber."""

import dataclasses
import json
from pathlib import Path

from fastapi import WebSocket

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
            except Exception:
                self._connections.remove(ws)


manager = ConnectionManager()


def _safe(obj):
    """Recursively convert an object to a JSON-serializable form."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _safe(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


async def on_signal(signal: Signal) -> None:
    """Forward every bus signal to all connected WebSocket clients."""
    if not manager._connections:
        return
    data = json.dumps({
        "type": signal.__class__.__name__,
        "title": signal.title,
        "details": _safe(signal.details),
    })
    await manager.broadcast(data)
