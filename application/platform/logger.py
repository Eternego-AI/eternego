"""Logging system with configurable media."""

import json
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from application.platform import datetimes


class Level(Enum):
    EMERGENCY = "emergency"
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    DEBUG = "debug"


class Message:
    def __init__(self, title: str, context: dict[str, Any], level: Level):
        self.id = str(uuid.uuid4())
        self.time = time.time_ns()
        self.title = title
        self.context = context
        self.level = level


_default_media: Callable[[Message], None] | None = None


def default_media(func: Callable[[Message], None]) -> Callable[[Message], None]:
    """Decorator to register a function as the default media."""
    global _default_media
    _default_media = func
    return func


def file_media(path: str | Path) -> Callable[[Message], None]:
    """Create a file media that writes logs to the specified file."""
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def media(message: Message) -> None:
        log_entry = {
            "id": message.id,
            "time": datetimes.iso_8601(datetimes.now()),
            "level": message.level.value,
            "title": message.title,
            "context": message.context,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    return media


def log(message: Message, *media: Callable[[Message], None]) -> None:
    if media:
        for m in media:
            m(message)
    elif _default_media:
        _default_media(message)


def emergency(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.EMERGENCY), *media)


def alert(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.ALERT), *media)


def critical(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.CRITICAL), *media)


def error(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.ERROR), *media)


def warning(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.WARNING), *media)


def notice(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.NOTICE), *media)


def info(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.INFO), *media)


def debug(title: str, context: dict[str, Any] | None = None, *media: Callable[[Message], None]) -> None:
    log(Message(title, context or {}, Level.DEBUG), *media)
