"""Signal subscription and dispatch system."""

import asyncio
import inspect
import time
import uuid
from typing import Any, Callable, Union, get_type_hints, get_origin, get_args


# === Signal Classes ===

class Signal:
    def __init__(self, title: str, details: dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.time = time.time_ns()
        self.title = title
        self.details = details


class Plan(Signal):
    pass


class Event(Signal):
    pass


class Message(Signal):
    pass


class Inquiry(Signal):
    pass


class Command(Signal):
    pass


# === Event Loop Reference ===

_loop = None


def set_loop(loop) -> None:
    """Store the main event loop. Called once at startup by the daemon."""
    global _loop
    _loop = loop


# === Subscription Registry ===

_handlers: list[tuple[type | tuple[type, ...], Callable]] = []


def subscribe(*handlers: Callable) -> None:
    for handler in handlers:
        signal_type = _get_signal_type(handler)
        if signal_type:
            _handlers.append((signal_type, handler))


async def send(*signals: Signal) -> list[Signal]:
    """Dispatch signals on the current async context. Use from async code."""
    results = []
    for signal in signals:
        for signal_type, handler in _handlers:
            if _matches(signal, signal_type):
                if inspect.iscoroutinefunction(handler):
                    result = await handler(signal)
                else:
                    result = handler(signal)
                if isinstance(result, Signal):
                    results.append(result)
    return results


def dispatch(*signals: Signal) -> None:
    """Dispatch signals from any context — async or thread. Fire and forget."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send(*signals))
    except RuntimeError:
        if _loop and _loop.is_running():
            asyncio.run_coroutine_threadsafe(send(*signals), _loop)


def _get_signal_type(handler: Callable) -> type | tuple[type, ...] | None:
    try:
        hints = get_type_hints(handler)
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())

        if not params:
            return None

        first_param = params[0].name
        hint = hints.get(first_param)

        if hint is None:
            return None

        origin = get_origin(hint)
        if origin is Union:
            return get_args(hint)

        return hint
    except Exception:
        return None


def _matches(signal: Signal, signal_type: type | tuple[type, ...]) -> bool:
    if isinstance(signal_type, tuple):
        return isinstance(signal, signal_type)
    return isinstance(signal, signal_type)
