"""Channels — open, close, send, and verify channel connections."""

from application.core import paths
from application.platform import logger, telegram, datetimes
from application.core.data import Channel, Message, Persona
from application.core.exceptions import ChannelError


async def send_all(persona: Persona, text: str) -> None:
    """Send text to all active channels for this persona."""
    from application.core import gateways
    for channel in gateways.of(persona).all_channels():
        await send(channel, text)


def keep_open(persona: Persona, channel: Channel) -> dict:
    """Return a channel strategy dict describing how to keep this channel alive.

    For polling channels (telegram): returns connection callable that polls once
    and returns a list of Message objects.
    """
    logger.info("Opening channel", {"type": channel.type, "persona": persona})
    if channel.type == "telegram":
        token = (channel.credentials or {})["token"]
        offset = [0]

        def connection():
            try:
                updates, offset[0] = telegram.poll(token, offset[0])
            except Exception:
                return []
            messages = []
            for text, chat_id, msg_id in telegram.direct_or_mentioned_in_group(persona.name, updates):
                msg_channel = Channel(type="telegram", name=chat_id, credentials=channel.credentials)
                messages.append(Message(channel=msg_channel, content=text, id=msg_id))
            return messages

        return {"type": "polling", "connection": connection}

    raise ChannelError(f"Unsupported channel type: {channel.type}")


async def express_thinking(persona: Persona) -> None:
    """Signal to all active channels that the persona is working on something."""
    from application.core import gateways
    for channel in gateways.of(persona).all_channels():
        if channel.type == "telegram":
            token = (channel.credentials or {})["token"]
            try:
                await telegram.async_typing_action(token, channel.name)
            except Exception:
                pass


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
