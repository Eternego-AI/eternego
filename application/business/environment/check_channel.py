"""Environment — verifying channel credentials are valid."""

from application.business.outcome import Outcome
from application.core import bus, channels
from application.core.exceptions import ChannelError


async def check_channel(channel_type: str, credentials: dict) -> Outcome[dict]:
    """Verify the channel credentials are valid and the connection works."""
    await bus.propose("Checking channel", {"type": channel_type})

    if channel_type != "telegram":
        await bus.broadcast("Channel check failed", {"type": channel_type, "reason": "unsupported"})
        return Outcome(success=False, message=f"Channel type '{channel_type}' is not supported.")

    try:
        await channels.show_typing(channel_type, credentials)
        await bus.broadcast("Channel is ready", {"type": channel_type})
        return Outcome(success=True, message="Channel is ready", data={"type": channel_type})

    except ChannelError as e:
        await bus.broadcast("Channel check failed", {"type": channel_type, "error": str(e)})
        return Outcome(success=False, message=str(e))

    except Exception as e:
        await bus.broadcast("Channel check failed", {"type": channel_type, "error": str(e)})
        return Outcome(success=False, message="Could not verify channel credentials. Please check and try again.")
