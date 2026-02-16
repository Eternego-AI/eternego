"""Channels — channel communication."""

from application.platform import logger, telegram
from application.core.data import Channel


def matches(ch: Channel, other: Channel) -> bool:
    """True if the two channels refer to the same channel."""
    logger.info("Matching channels", {"name": ch.name, "other_name": other.name})
    if ch.name != other.name:
        return False
    return (ch.credentials or {}) == (other.credentials or {})


async def send(ch: Channel, message: str) -> dict:
    """Send a message through a channel."""
    logger.info("Sending message through channel", {"name": ch.name})
    if ch.name == "telegram":
        return await telegram.send(
            token=ch.credentials["token"],
            chat_id=ch.credentials["chat_id"],
            message=message,
        )
    return {}


async def assert_receives(ch: Channel, message: str) -> bool:
    """Send a message and verify the channel received it."""
    logger.info("Asserting channel receives message", {"name": ch.name})
    response = await send(ch, message)
    if ch.name == "telegram":
        return response.get("ok", False)
    return False
