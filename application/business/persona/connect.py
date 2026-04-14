"""Persona — opening a channel connection."""

from application.business.outcome import Outcome
from application.core import bus, channels, gateways
from application.core.data import Channel, Message, Persona
from application.core.exceptions import ChannelError

from .hear import hear
from .pair import pair


async def connect(persona: Persona, channel: Channel) -> Outcome[None]:
    """Open a connection for a channel and register it."""
    await bus.propose("Connecting channel", {"persona": persona, "channel": channel})
    try:
        if gateways.of(persona).has_channel(channel):
            await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
            return Outcome(success=True, message="")

        if channel.type == "web":
            gateways.of(persona).add(channel, {"type": "web"})
        else:
            async def on_message(message: Message) -> Outcome:
                if channel.verified_at is not None:
                    return await hear(persona, message)

                outcome = await pair(persona, message.channel)
                if not outcome.success:
                    await channels.send(message.channel, outcome.message)
                else:
                    code = outcome.data.pairing_code
                    await channels.send(
                        message.channel,
                        f"Your pairing code is: {code}\n\nRun: eternego pair {code}\n\nThis code expires in 10 minutes.",
                    )
                return outcome

            strategy = channels.keep_open(persona, channel)
            strategy["on_message"] = on_message
            gateways.of(persona).add(channel, strategy)

        await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
        return Outcome(success=True, message="")
    except ChannelError as e:
        await bus.broadcast("Channel connection failed", {"persona": persona, "channel": channel, "error": str(e)})
        return Outcome(success=False, message=str(e))
