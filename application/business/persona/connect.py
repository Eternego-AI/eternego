"""Persona — connecting a channel.

Produces the connection for a channel: a poll callable for channels that
need polling, an async message handler, and a close callable. The caller
(the agent) is responsible for keeping it alive.
"""

import secrets
from dataclasses import dataclass
from typing import Callable

from application.business.outcome import Outcome
from application.core import bus, channels
from application.core.data import Channel, Persona
from application.core.exceptions import ChannelError
from application.platform import datetimes


@dataclass
class ConnectData:
    channel: Channel
    poll: Callable | None           # poll once and return messages; None for passive channels
    handle_message: Callable | None  # async handler for incoming messages; None for passive channels
    close: Callable                  # release underlying resources


async def connect(persona: Persona, channel: Channel, pairing_codes: dict) -> Outcome[ConnectData]:
    """Connect the channel. Web channels are passive; others need polling.

    For non-web channels, incoming messages are routed: verified → hear,
    unverified → generate a pairing code and send instructions back.
    """
    await bus.propose("Connecting channel", {"persona": persona, "channel": channel})
    try:
        if channel.type == "web":
            await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
            return Outcome(success=True, message="", data=ConnectData(
                channel=channel,
                poll=None,
                handle_message=None,
                close=lambda: None,
            ))

        strategy = channels.keep_open(persona, channel)

        async def handle_message(message):
            if channel.verified_at is not None:
                from .hear import hear
                return await hear(persona, message)

            while True:
                code = secrets.token_hex(3).upper()
                if code not in pairing_codes:
                    break
            pairing_codes[code] = {
                "channel_type": message.channel.type,
                "channel_name": message.channel.name,
                "created_at": datetimes.now(),
            }
            await channels.send(
                message.channel,
                f"Your pairing code is: {code}\n\n"
                "Enter this code in the Eternego web UI to verify this channel.\n\n"
                "This code expires in 10 minutes.",
            )

        await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
        return Outcome(success=True, message="", data=ConnectData(
            channel=channel,
            poll=strategy["connection"],
            handle_message=handle_message,
            close=lambda: None,
        ))

    except ChannelError as e:
        await bus.broadcast("Channel connection failed", {"persona": persona, "channel": channel, "error": str(e)})
        return Outcome(success=False, message=str(e))
