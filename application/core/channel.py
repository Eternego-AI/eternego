"""Channel — channel communication."""

from application.platform import logger, telegram
from application.core.data import Channel


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
