"""Persona — generating a pairing code for channel verification."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents, bus
from application.core.data import Channel, Persona


@dataclass
class PairData:
    pairing_code: str


async def pair(persona: Persona, channel: Channel) -> Outcome[PairData]:
    """Generate a pairing code so the person can verify a new channel."""
    await bus.propose("Pairing channel", {"persona": persona, "channel": channel})

    if channel.verified_at is not None:
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "already_verified"})
        return Outcome(success=False, message="This channel is already verified.")

    if not any(ch.type == channel.type for ch in (persona.channels or [])):
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "not_belonging"})
        return Outcome(success=False, message="This channel does not belong to this persona.")

    code = agents.pair(persona, channel)
    await bus.broadcast("Channel pairing started", {"persona": persona, "channel": channel})
    return Outcome(success=True, message="Pairing code generated.", data=PairData(pairing_code=code))
