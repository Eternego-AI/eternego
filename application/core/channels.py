"""Channels — open, close, send, and verify channel connections."""

from application.core import paths
from application.platform import logger, telegram, datetimes
from application.core.data import Channel, Persona
from application.core.exceptions import ChannelError


async def send_all(channels: list, text: str) -> None:
    """Send text to each channel in the list."""
    for channel in channels:
        await send(channel, text)


def keep_open(persona: Persona, channel: Channel, commands: list[dict] | None = None) -> dict:
    """Return a channel strategy dict describing how to keep this channel alive.

    For polling channels (telegram): registers commands, returns a poll callable
    that dispatches signals for messages and commands.
    """
    logger.info("Opening channel", {"type": channel.type, "persona": persona})
    if channel.type == "telegram":
        token = (channel.credentials or {})["token"]
        offset = [0]
        filter_fn = telegram.direct_or_mentioned(persona.name)
        context = {"channel_type": "telegram"}

        if commands:
            try:
                telegram.set_commands(token, commands)
            except Exception as e:
                logger.warning("Failed to set Telegram commands", {"error": str(e)})

        def connection():
            try:
                offset[0] = telegram.poll(token, offset[0], context, filter_fn)
            except Exception:
                pass

        return {"type": "polling", "connection": connection}

    raise ChannelError(f"Unsupported channel type: {channel.type}")


async def show_typing(channel_type: str, credentials: dict) -> None:
    """Send a typing indicator on the channel. No-op for unsupported types."""
    logger.info("Showing typing", {"type": channel_type})
    if channel_type == "telegram":
        token = (credentials or {}).get("token", "")
        bot = telegram.get_me(token)
        await telegram.async_typing_action(token, bot["result"]["id"])



async def send(channel: Channel, text: str) -> None:
    """Send text to a specific channel."""
    logger.info("Sending on channel", {"type": channel.type, "text": text[:50]})
    try:
        if channel.type == "telegram":
            token = (channel.credentials or {})["token"]
            await telegram.async_send(token, channel.name, text)
        else:
            await channel.bus.put(text)
    except Exception as e:
        logger.error("Failed to send on channel", {"type": channel.type, "error": str(e)})


def verify(persona: Persona, channel: Channel, name: str) -> None:
    channel.name = name
    channel.verified_at = datetimes.iso_8601(datetimes.now())
    paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)
