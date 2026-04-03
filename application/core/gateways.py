"""Gateways — per-persona connection registry, process-lived."""

import asyncio
import inspect
import threading

from application.core.data import Channel, Persona
from application.platform import logger

_active: dict[str, list[tuple[Channel, dict]]] = {}


def _key(channel: Channel) -> str:
    return f"{channel.type}:{channel.name}"


def of(persona: Persona) -> "Connections":
    """Return the active connections for this persona."""
    return Connections(persona)


class Connections:
    """All active channel connections for one persona. Use via gateways.of(persona)."""

    def __init__(self, persona: Persona):
        self._id = persona.id

    def add(self, channel: Channel, strategy: dict) -> None:
        """Register a channel strategy and start it if it's a polling type.

        Captures the running event loop so messages from polling threads
        are dispatched to the main loop regardless of handler type.
        """
        _active.setdefault(self._id, []).append((channel, strategy))

        if strategy.get("type") == "polling":
            connection = strategy["connection"]
            on_message = strategy.get("on_message")
            loop = asyncio.get_running_loop()

            def dispatch(msg):
                if inspect.iscoroutinefunction(on_message):
                    asyncio.run_coroutine_threadsafe(on_message(msg), loop)
                else:
                    on_message(msg)

            def poll_loop():
                while self.has_channel(channel):
                    try:
                        messages = connection()
                        if on_message and messages:
                            for msg in messages:
                                dispatch(msg)
                    except Exception as e:
                        logger.warning("Gateway polling error", {"channel": _key(channel), "error": str(e)})

            thread = threading.Thread(target=poll_loop, daemon=True)
            thread.start()

    def remove(self, channel: Channel) -> None:
        """Remove a channel. Its polling thread will stop on next iteration."""
        pairs = _active.get(self._id, [])
        key = _key(channel)
        for i, (ch, _) in enumerate(pairs):
            if _key(ch) == key:
                pairs.pop(i)
                return

    def has_channel(self, channel: Channel) -> bool:
        """Return True if a connection for this channel is already registered."""
        key = _key(channel)
        return any(_key(ch) == key for ch, _ in _active.get(self._id, []))

    def all_channels(self) -> list[Channel]:
        """Return all active channels for this persona."""
        return [ch for ch, _ in _active.get(self._id, [])]

    def clear(self) -> None:
        """Remove all connections for this persona. Polling threads will stop."""
        _active.pop(self._id, None)
