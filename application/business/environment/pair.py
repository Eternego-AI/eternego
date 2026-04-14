"""Environment — claiming a pairing code and verifying a channel."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents, bus, channels
from application.core.exceptions import AgentError
from application.core.data import Persona, Channel


@dataclass
class PairData:
    persona: Persona
    channel: Channel


async def pair(code: str) -> Outcome[PairData]:
    """Claim a pairing code and mark the channel as verified for the persona."""
    await bus.propose("Pairing channel", {"code": code})

    try:
        persona, channel_type, channel_name = agents.take_code(code)

        channel = next(
            (ch for ch in (persona.channels or []) if ch.type == channel_type), None
        )
        if not channel:
            await bus.broadcast(
                "Pairing failed", {"code": code, "reason": "invalid_channel"}
            )
            return Outcome(
                success=False,
                message="The channel associated with this pairing code could not be found.",
            )

        if channel.verified_at:
            await bus.broadcast(
                "Pairing failed", {"code": code, "reason": "already_verified"}
            )
            return Outcome(success=False, message="This channel is already verified.")

        channels.verify(persona, channel, channel_name)

        await bus.broadcast(
            "Channel paired", {"persona": persona, "channel": channel}
        )
        return Outcome(
            success=True,
            message="Channel paired successfully",
            data=PairData(persona=persona, channel=channel),
        )

    except AgentError as e:
        await bus.broadcast("Pairing failed", {"code": code, "reason": str(e)})
        return Outcome(success=False, message=str(e))
