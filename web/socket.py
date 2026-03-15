"""WebSocket connection manager and signal subscriber."""

import asyncio
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


class WebSocketBus:
    """An asyncio.Queue-compatible bus that broadcasts to all connected WebSocket tabs.

    Matches the Queue interface so it can be used as channel.bus.
    Messages put into this bus are forwarded to every connected browser tab
    as a JSON payload with type="chat_message", and also made available to
    the awaiting get() call in persona.talk().
    """

    def __init__(self, persona_id: str):
        self._persona_id = persona_id
        self._queue: asyncio.Queue = asyncio.Queue()

    async def put(self, text: str) -> None:
        """Broadcast a chat message to WebSocket clients and resolve the waiting caller."""
        data = json.dumps({
            "type": "chat_message",
            "persona_id": self._persona_id,
            "content": text,
        })
        await manager.broadcast(data)
        await self._queue.put(text)

    async def get(self) -> str:
        """Wait for the next response from the conscious pipeline."""
        return await self._queue.get()


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
