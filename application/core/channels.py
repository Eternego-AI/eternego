"""Channels — open, close, send, and verify channel connections."""

import asyncio
import threading
from collections.abc import Callable

from application.core import paths
from application.platform import logger, telegram, datetimes
from application.core.data import Channel, Message, Persona
from application.core.exceptions import ChannelError


async def send_all(persona: Persona, text: str) -> None:
    """Send text to all active channels for this persona."""
    from application.core import gateways
    for channel in gateways.of(persona).all_channels():
        await send(channel, text)


def keep_open(persona: Persona, channel: Channel, on_message: Callable) -> Callable[[], None]:
    """Open a persistent connection for a channel and return a stop callable."""
    logger.info("Opening channel", {"type": channel.type, "persona": persona})
    if channel.type == "telegram":
        token = (channel.credentials or {})["token"]
        stop_event = threading.Event()
        loop = asyncio.get_running_loop()

        def bridge(text: str, chat_id: str, message_id: str):
            msg_channel = Channel(type="telegram", name=chat_id, credentials=channel.credentials)
            message = Message(channel=msg_channel, content=text, id=message_id)

            async def handle():
                await on_message(message)

            asyncio.run_coroutine_threadsafe(handle(), loop)

        def on_error(exc: Exception):
            logger.warning("Telegram polling error", {"persona": persona, "error": str(exc)})

        thread = threading.Thread(
            target=telegram.poll,
            kwargs={
                "token": token,
                "username": persona.name,
                "on_message": bridge,
                "stop": lambda: stop_event.is_set(),
                "on_error": on_error,
            },
            daemon=True,
        )
        thread.start()
        return stop_event.set
    raise ChannelError(f"Unsupported channel type: {channel.type}")



async def express_thinking(persona: Persona) -> None:
    """Signal to all active channels that the persona is working on something."""
    from application.core import gateways
    for channel in gateways.of(persona).all_channels():
        if channel.type == "telegram":
            token = (channel.credentials or {})["token"]
            try:
                await asyncio.to_thread(telegram.typing_action, token=token, chat_id=channel.name)
            except Exception:
                pass


async def send(channel: Channel, text: str) -> None:
    """Send text to a specific channel."""
    logger.info("Sending on channel", {"type": channel.type, "text": text[:50]})
    try:
        if channel.type == "telegram":
            token = (channel.credentials or {})["token"]
            await asyncio.to_thread(telegram.send, token=token, chat_id=channel.name, message=text)
        else:
            await channel.bus.put(text)
    except Exception as e:
        logger.error("Failed to send on channel", {"type": channel.type, "error": str(e)})

def verify(persona: Persona, channel: Channel, name: str) -> None:
    channel.name = name
    channel.verified_at = datetimes.iso_8601(datetimes.now())
    paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)
