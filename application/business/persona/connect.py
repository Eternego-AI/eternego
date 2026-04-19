"""Persona — connecting a channel.

Produces the connection for a channel: a poll callable for channels that
need polling and a close callable. The caller (the agent) is responsible
for keeping it alive. Messages and commands arrive as signals dispatched
by the platform layer.
"""

from dataclasses import dataclass
from typing import Callable

from application.business.outcome import Outcome
from application.core import bus, channels
from application.core.data import Channel, Persona
from application.core.exceptions import ChannelError


@dataclass
class ConnectData:
    channel: Channel
    poll: Callable | None           # poll once; None for passive channels
    close: Callable                  # release underlying resources


async def connect(persona: Persona, channel: Channel, commands: list[dict] | None = None) -> Outcome[ConnectData]:
    """Connect the channel. Web channels are passive; others need polling.

    Messages and commands are dispatched as signals by the platform poll.
    Pairing is handled via the /start command.
    """
    bus.propose("Connecting channel", {"persona": persona, "channel": channel})
    try:
        if channel.type == "web":
            bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
            return Outcome(success=True, message="", data=ConnectData(
                channel=channel,
                poll=None,
                close=lambda: None,
            ))

        strategy = channels.keep_open(persona, channel, commands)

        bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
        return Outcome(success=True, message="", data=ConnectData(
            channel=channel,
            poll=strategy["connection"],
            close=lambda: None,
        ))

    except ChannelError as e:
        bus.broadcast("Channel connection failed", {"persona": persona, "channel": channel, "error": str(e)})
        return Outcome(success=False, message=str(e))
