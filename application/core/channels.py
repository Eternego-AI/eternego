"""Channels — channel communication."""

import asyncio
import threading
import urllib.error
from collections.abc import Callable, Coroutine

from application.platform import logger, telegram
from application.core.data import Channel, Gateway, Persona
from application.core.exceptions import ChannelError


def matches(ch: Channel, other: Channel) -> bool:
    """True if the two channels refer to the same channel."""
    logger.info("Matching channels", {"name": ch.name, "other_name": other.name})
    if ch.name != other.name:
        return False
    return (ch.credentials or {}) == (other.credentials or {})


async def send(ch: Channel, message: str) -> dict:
    """Send a message through a channel."""
    logger.info("Sending message through channel", {"name": ch.name})
    try:
        if ch.name == "telegram":
            return await asyncio.to_thread(
                telegram.send,
                token=ch.credentials["token"],
                chat_id=ch.credentials["chat_id"],
                message=message,
            )
        return {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        raise ChannelError(f"Failed to send message through {ch.name}: {e}") from e


async def assert_receives(ch: Channel, message: str) -> bool:
    """Send a message and verify the channel received it."""
    logger.info("Asserting channel receives message", {"name": ch.name})
    try:
        response = await send(ch, message)
    except ChannelError:
        return False
    if ch.name == "telegram":
        return response.get("ok", False)
    return False


def listen(persona: Persona, ch: Channel, on_message: Callable[[str], Coroutine[None, None, None]]) -> Gateway:
    """Listen for incoming messages on a channel. Returns a gateway."""
    logger.info("Listening on channel", {"name": ch.name, "persona": persona.id})
    loop = asyncio.get_running_loop()
    def bridge(text: str):
        asyncio.run_coroutine_threadsafe(on_message(text), loop)

    if ch.name != "telegram":
        raise ChannelError(f"Unsupported channel: {ch.name}")

    gw = Gateway(channel=ch, threading=threading)

    thread = gw.threading.Thread(
        target=telegram.poll,
        kwargs={
            "token": ch.credentials["token"],
            "chat_id": ch.credentials["chat_id"],
            "username": persona.name,
            "on_message": bridge,
            "stop": lambda: gw.is_stopped,
        },
        daemon=True,
    )
    thread.start()

    return gw
