"""Persona — closing a channel connection."""

from application.business.outcome import Outcome
from application.core import bus, gateways
from application.core.data import Channel, Persona


async def disconnect(persona: Persona, channel: Channel) -> Outcome:
    """Close a channel connection for a persona."""
    await bus.propose("Disconnecting channel", {"persona": persona, "channel": channel})
    stop = gateways.of(persona).remove(channel)
    if stop:
        stop()
    await bus.broadcast("Channel disconnected", {"persona": persona, "channel": channel})
    return Outcome(success=True, message="")
