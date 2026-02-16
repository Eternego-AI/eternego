"""Gateway — managing communication channels for a persona."""

from application.core import bus, channels
from application.core.data import Channel
from application.business.outcome import Outcome


async def verify_channel(channel: Channel) -> Outcome[dict]:
    """Verify a communication channel is alive and working."""
    await bus.propose("Verifying channel", {"channel": channel})

    if not await channels.assert_receives(channel, "Welcome to Eternego!"):
        await bus.broadcast("Channel verification failed", {"channel": channel})
        return Outcome(success=False, message=f"Could not connect to {channel.name}. Please check your credentials.")

    await bus.broadcast("Channel verified", {"channel": channel})

    return Outcome(success=True, message="Channel verified successfully", data={"name": channel.name})
