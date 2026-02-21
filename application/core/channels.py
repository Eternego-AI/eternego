"""Channels — open, close, send, and verify channel connections."""

import asyncio
import secrets
import threading
from collections.abc import Callable

from application.platform import filesystem, logger, telegram
from application.core import paths
from application.core.data import Channel, Message, Persona
from application.core.exceptions import ChannelError


# ── Open / Close ──────────────────────────────────────────────────────────────

def open(persona: Persona, channel: Channel, on_message: Callable) -> Callable[[], None]:
    """Open a persistent connection for a channel and return a stop callable."""
    logger.info("Opening channel", {"type": channel.type, "persona": persona.id})
    if channel.type == "telegram":
        return _open_telegram(persona, channel, on_message)
    raise ChannelError(f"Unsupported channel type: {channel.type}")


def _open_telegram(persona: Persona, channel: Channel, on_message: Callable) -> Callable[[], None]:
    token = (channel.credentials or {})["token"]
    stop_event = threading.Event()
    loop = asyncio.get_running_loop()

    def bridge(text: str, chat_id: str):
        msg_channel = Channel(type="telegram", name=chat_id, credentials=channel.credentials)
        message = Message(channel=msg_channel, content=text)

        async def handle():
            outcome = await on_message(message)
            if outcome.success:
                await asyncio.to_thread(telegram.typing_action, token=token, chat_id=chat_id)

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


# ── Send ──────────────────────────────────────────────────────────────────────

async def send(channel: Channel, text: str) -> None:
    """Send text to a specific channel."""
    logger.info("Sending on channel", {"type": channel.type, "text": text[:50]})
    if channel.type == "telegram":
        token = (channel.credentials or {})["token"]
        await asyncio.to_thread(telegram.send, token=token, chat_id=channel.name, message=text)
    elif channel.type == "web" and channel.bus is not None:
        await channel.bus.put(text)


# ── Verified channel list (disk-backed) ───────────────────────────────────────

def is_verified(persona: Persona, channel: Channel) -> bool:
    """Return True if this channel is verified for the persona."""
    logger.info("Checking verified channel", {"persona": persona.id})
    try:
        content = filesystem.read(paths.channels(persona.id))
        for line in content.splitlines():
            parts = line.strip().split(":", 2)
            if len(parts) == 3 and parts[0] == channel.type and parts[1] == channel.name:
                verified_at = parts[2]
                return bool(verified_at)
        return False
    except OSError:
        return False


def pair(persona: Persona, channel: Channel) -> str:
    """Generate and return a pairing code for an unverified channel."""
    logger.info("Generating pairing code", {"persona": persona.id})
    return secrets.token_hex(3).upper()


def save(persona: Persona, channel: Channel) -> None:
    """Persist a verified channel for the persona, updating the record if it already exists."""
    logger.info("Saving verified channel", {"persona": persona.id})
    try:
        path = paths.channels(persona.id)
        entry = f"{channel.type}:{channel.name}:{channel.verified_at}"
        try:
            lines = filesystem.read(path).splitlines()
            prefix = f"{channel.type}:{channel.name}:"
            updated = [entry if line.startswith(prefix) else line for line in lines]
            if updated == lines:
                updated.append(entry)
            filesystem.write(path, "\n".join(updated) + "\n")
        except OSError:
            filesystem.write(path, entry + "\n")
    except OSError as e:
        raise ChannelError("Failed to save verified channel") from e
