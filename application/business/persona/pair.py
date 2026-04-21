"""Environment — verifying a channel after a pairing code is claimed."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Persona, Channel
from application.platform import datetimes


@dataclass
class PairData:
    persona: Persona
    channel: Channel


async def pair(persona: Persona, channel: Channel) -> Outcome[PairData]:
    """Verify a channel for a persona after the pairing code has been claimed."""
    bus.propose("Pairing channel", {"persona": persona, "channel": channel})

    existing = next(
        (ch for ch in (persona.channels or []) if ch.type == channel.type), None
    )
    if not existing:
        bus.broadcast("Pairing failed", {"persona": persona, "reason": "invalid_channel"})
        return Outcome(
            success=False,
            message="The channel associated with this pairing code could not be found.",
        )

    if existing.verified_at:
        bus.broadcast("Pairing failed", {"persona": persona, "reason": "already_verified"})
        return Outcome(success=False, message="This channel is already verified.")

    existing.name = channel.name
    existing.verified_at = datetimes.iso_8601(datetimes.now())
    paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

    bus.broadcast("Channel paired", {"persona": persona, "channel": existing})
    return Outcome(
        success=True,
        message="Channel paired successfully",
        data=PairData(persona=persona, channel=existing),
    )
