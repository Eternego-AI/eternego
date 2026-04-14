"""Environment — verifying a channel after a pairing code is claimed."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, channels
from application.core.data import Persona, Channel


@dataclass
class PairData:
    persona: Persona
    channel: Channel


async def pair(persona: Persona, channel_type: str, channel_name: str) -> Outcome[PairData]:
    """Verify a channel for a persona after the pairing code has been claimed."""
    await bus.propose("Pairing channel", {"persona": persona, "channel_type": channel_type})

    channel = next(
        (ch for ch in (persona.channels or []) if ch.type == channel_type), None
    )
    if not channel:
        await bus.broadcast("Pairing failed", {"persona": persona, "reason": "invalid_channel"})
        return Outcome(
            success=False,
            message="The channel associated with this pairing code could not be found.",
        )

    if channel.verified_at:
        await bus.broadcast("Pairing failed", {"persona": persona, "reason": "already_verified"})
        return Outcome(success=False, message="This channel is already verified.")

    channels.verify(persona, channel, channel_name)

    await bus.broadcast("Channel paired", {"persona": persona, "channel": channel})
    return Outcome(
        success=True,
        message="Channel paired successfully",
        data=PairData(persona=persona, channel=channel),
    )
