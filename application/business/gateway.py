"""Gateway — managing communication channels for a persona."""

from application.core import bus, channel
from application.core.data import Channel
from application.business.outcome import Outcome


async def verify_channel(ch: Channel) -> Outcome[dict]:
    """Verify a communication channel is alive and working."""
    await bus.propose("Verifying channel", {"name": ch.name})

    if not await channel.assert_receives(ch, "Welcome to Eternego!"):
        await bus.broadcast("Channel verification failed", {"name": ch.name})
        return Outcome(success=False, message=f"Could not connect to {ch.name}. Please check your credentials.")

    await bus.broadcast("Channel verified", {"name": ch.name})

    return Outcome(success=True, message="Channel verified successfully", data={"name": ch.name})
