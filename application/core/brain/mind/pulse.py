"""Pulse — the brain's runtime state.

Wraps the platform worker (generic async executor) with domain state:
situation (wake/normal/sleep) and the cognitive event log (success/fault
per brain function) that health_check reads to decide what to do.
"""

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Event:
    kind: str                         # "success" | "fault"
    function: str                     # e.g. "realize", "recognize"
    loop: int
    provider: str | None = None
    url: str | None = None
    model_name: str | None = None
    error: str | None = None
    time: float = field(default_factory=time.time)


_EVENT_LOG_CAPACITY = 200


class Pulse:
    def __init__(self, worker):
        self.worker = worker
        self.situation = None
        self._events: deque[Event] = deque(maxlen=_EVENT_LOG_CAPACITY)
        self._loop_number: int = 0

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    @property
    def loop_number(self) -> int:
        return self._loop_number

    def next_loop(self) -> None:
        """Bump the loop counter. Tick calls this at the top of each while iteration."""
        self._loop_number += 1

    def log_success(self, function: str) -> None:
        self._events.append(Event(kind="success", function=function, loop=self._loop_number))

    def log_fault(
        self,
        function: str,
        provider: str | None = None,
        url: str | None = None,
        model_name: str | None = None,
        error: str | None = None,
    ) -> None:
        self._events.append(Event(
            kind="fault",
            function=function,
            loop=self._loop_number,
            provider=provider,
            url=url,
            model_name=model_name,
            error=error,
        ))

    def clear_events(self) -> None:
        self._events.clear()
