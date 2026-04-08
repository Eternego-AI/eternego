"""Environment — claiming a pairing code and verifying a channel."""

from application.business.outcome import Outcome
from application.core import agents, bus, channels
from application.core.exceptions import AgentError


async def pair(code: str) -> Outcome[dict]:
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
            "Channel paired", {"persona_id": persona.id, "channel": channel.name}
        )
        return Outcome(
            success=True,
            message="Channel paired successfully",
            data={"persona_id": persona.id, "channel": channel.name},
        )

    except AgentError as e:
        await bus.broadcast("Pairing failed", {"code": code, "reason": str(e)})
        return Outcome(success=False, message=str(e))
