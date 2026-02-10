"""Event bus for signal dispatch."""

from typing import Any

from application.platform.observer import Signal, Plan, Event, Message, Inquiry, Command, send
from application.platform import logger


async def propose(title: str, details: dict[str, Any]) -> list[Signal]:
    logger.info(title, details)
    return await send(Plan(title, details))


async def broadcast(title: str, details: dict[str, Any]) -> list[Signal]:
    logger.info(title, details)
    return await send(Event(title, details))


async def share(title: str, details: dict[str, Any]) -> list[Signal]:
    logger.info(title, details)
    return await send(Message(title, details))


async def ask(title: str, details: dict[str, Any]) -> list[Signal]:
    logger.info(title, details)
    return await send(Inquiry(title, details))


async def order(title: str, details: dict[str, Any]) -> list[Signal]:
    logger.info(title, details)
    return await send(Command(title, details))
