"""Channels — open, close, send, and verify channel connections."""

import asyncio
import threading
from collections.abc import Callable

from application.platform import logger, telegram
from application.core.data import Channel, Message, Persona
from application.core.exceptions import ChannelError


_latest: dict[str, "Channel"] = {}


def set_latest(persona: Persona, channel: "Channel") -> None:
    """Record the most recently active channel for this persona."""
    _latest[persona.id] = channel


def latest(persona: Persona) -> "Channel | None":
    """Return the most recently active channel for this persona."""
    return _latest.get(persona.id)


def keep_open(persona: Persona, channel: Channel, on_message: Callable) -> Callable[[], None]:
    """Open a persistent connection for a channel and return a stop callable."""
    logger.info("Opening channel", {"type": channel.type, "persona": persona.id})
    if channel.type == "telegram":
        token = (channel.credentials or {})["token"]
        stop_event = threading.Event()
        loop = asyncio.get_running_loop()

        def bridge(text: str, chat_id: str):
            msg_channel = Channel(type="telegram", name=chat_id, credentials=channel.credentials)
            message = Message(channel=msg_channel, content=text)

            async def handle():
                await on_message(message)

            asyncio.run_coroutine_threadsafe(handle(), loop)

        def on_error(exc: Exception):
            logger.warning("Telegram polling error", {"persona": persona.id, "error": str(exc)})

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



def default_channel(persona: Persona) -> Channel | None:
    """Return the first active channel for a persona, or None if none are open."""
    from application.core import gateways
    active = gateways.of(persona).all_channels()
    return active[0] if active else None


async def express_thinking(persona: Persona) -> None:
    """Signal to the active channel that the persona is working on something."""
    channel = latest(persona) or default_channel(persona)
    if channel is None:
        return
    if channel.type == "telegram":
        token = (channel.credentials or {})["token"]
        try:
            await asyncio.to_thread(telegram.typing_action, token=token, chat_id=channel.name)
        except Exception:
            pass


async def send(channel: Channel, text: str) -> None:
    """Send text to a specific channel."""
    logger.info("Sending on channel", {"type": channel.type, "text": text[:50]})
    if channel.type == "telegram":
        token = (channel.credentials or {})["token"]
        await asyncio.to_thread(telegram.send, token=token, chat_id=channel.name, message=text)
    else:
        await channel.bus.put(text)

