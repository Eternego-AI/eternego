"""Gateways — per-persona connection registry, process-lived."""

from collections.abc import Callable

from application.core.data import Channel, Persona

_active: dict[str, list[tuple[Channel, Callable[[], None]]]] = {}


def _key(channel: Channel) -> str:
    return f"{channel.type}:{channel.name}"


def of(persona: Persona) -> "Connections":
    """Return the active connections for this persona."""
    return Connections(persona)


class Connections:
    """All active channel connections for one persona. Use via gateways.of(persona)."""

    def __init__(self, persona: Persona):
        self._id = persona.id

    def add(self, channel: Channel, stop: Callable[[], None]) -> None:
        """Register a stop callable for a channel."""
        _active.setdefault(self._id, []).append((channel, stop))

    def remove(self, channel: Channel) -> Callable[[], None] | None:
        """Remove and return the stop callable for a channel, or None if not found."""
        pairs = _active.get(self._id, [])
        key = _key(channel)
        for i, (ch, stop) in enumerate(pairs):
            if _key(ch) == key:
                pairs.pop(i)
                return stop
        return None

    def clear(self) -> None:
        """Stop and remove all connections for this persona."""
        for _, stop in _active.get(self._id, []):
            stop()
        _active.pop(self._id, None)
