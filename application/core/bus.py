"""Event bus for signal dispatch."""

from typing import Any

from application.platform.observer import Plan, Event, Message, Inquiry, Command, dispatch


def propose(title: str, details: dict[str, Any]) -> None:
    dispatch(Plan(title, details))


def broadcast(title: str, details: dict[str, Any]) -> None:
    dispatch(Event(title, details))


def share(title: str, details: dict[str, Any]) -> None:
    dispatch(Message(title, details))


def ask(title: str, details: dict[str, Any]) -> None:
    dispatch(Inquiry(title, details))


def order(title: str, details: dict[str, Any]) -> None:
    dispatch(Command(title, details))
