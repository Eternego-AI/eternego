"""Environment — verifying channel credentials are valid."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, channels
from application.core.data import Channel
from application.core.exceptions import ChannelError


@dataclass
class CheckChannelData:
    channel: Channel


async def check_channel(channel_type: str, credentials: dict) -> Outcome[CheckChannelData]:
    """Verify the channel credentials are valid and the connection works."""
    await bus.propose("Checking channel", {"type": channel_type})

    try:
        if channel_type == "telegram":
            await channels.show_typing(channel_type, credentials)

        channel = Channel(type=channel_type, credentials=credentials)
        await bus.broadcast("Channel is ready", {"type": channel_type})
        return Outcome(success=True, message="Channel is ready", data=CheckChannelData(channel=channel))

    except ChannelError as e:
        await bus.broadcast("Channel check failed", {"type": channel_type, "error": str(e)})
        return Outcome(success=False, message=str(e))

    except Exception as e:
        await bus.broadcast("Channel check failed", {"type": channel_type, "error": str(e)})
        return Outcome(success=False, message="Could not verify channel credentials. Please check and try again.")
