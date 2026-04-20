"""Worker — serial job executor backed by asyncio.

Runs a loop function (tick) and dispatches individual jobs within it.
One job at a time — jobs are cancellable. The loop restarts on nudge
when idle.

Also keeps a ring-buffered event log the tick writes to (success/fault per
function call) so health_check can see how the body has been feeling.
"""

import asyncio
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Event:
    kind: str                         # "success" | "fault"
    function: str                     # e.g. "realize"
    loop: int
    provider: str | None = None
    url: str | None = None
    model_name: str | None = None
    error: str | None = None
    time: float = field(default_factory=time.time)


_EVENT_LOG_CAPACITY = 200


class Worker:
    """Serial async executor. One per persona, outlives ego reloads."""

    def __init__(self):
        self._tick_fn: Callable | None = None
        self._tick_args: tuple = ()
        self._tick_task: asyncio.Task | None = None
        self._job: asyncio.Task | None = None
        self._error: Exception | None = None
        self._stopped: bool = False
        self._events: deque[Event] = deque(maxlen=_EVENT_LOG_CAPACITY)
        self._loop_number: int = 0

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self, fn: Callable, *args) -> None:
        """Set the tick function and start it."""
        self._tick_fn = fn
        self._tick_args = args
        self._stopped = False
        self._error = None
        if not self._tick_task or self._tick_task.done():
            self._tick_task = asyncio.create_task(self._loop())

    async def _loop(self):
        """Run tick, storing any unhandled exception."""
        if not self._tick_fn:
            return
        try:
            await self._tick_fn(*self._tick_args)
        except Exception as e:
            self._error = e

    # ── Job dispatch ──────────────────────────────────────────────────────

    async def dispatch(self, fn: Callable, *args):
        """Run a single job. Returns result, or None if cancelled/stopped."""
        if self._stopped:
            return None
        self._job = asyncio.create_task(fn(*args))
        try:
            return await self._job
        except asyncio.CancelledError:
            return None
        finally:
            self._job = None

    def cancel(self) -> None:
        """Cancel the currently running job (not the tick loop)."""
        if self._job and not self._job.done():
            self._job.cancel()

    # ── Nudge ─────────────────────────────────────────────────────────────

    def nudge(self) -> None:
        """Signal new work. Start tick if idle, cancel current job if running."""
        if self._stopped:
            return
        if not self._tick_task or self._tick_task.done():
            if self._tick_fn:
                self._tick_task = asyncio.create_task(self._loop())
        else:
            self.cancel()

    # ── Settle & stop ─────────────────────────────────────────────────────

    async def settle(self, timeout: float = 1800) -> None:
        """Wait for tick to finish naturally. Force-stop on timeout."""
        if self._tick_task and not self._tick_task.done():
            done, _ = await asyncio.wait({self._tick_task}, timeout=timeout)
            if not done:
                await self.stop()

    async def stop(self) -> None:
        """Stop processing. Tick exits cooperatively after current dispatch."""
        self._stopped = True
        self.cancel()
        if self._tick_task and not self._tick_task.done():
            try:
                await self._tick_task
            except Exception:
                pass

    # ── Status ────────────────────────────────────────────────────────────

    @property
    def idle(self) -> bool:
        return not self._tick_task or self._tick_task.done()

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def error(self) -> Exception | None:
        return self._error

    def reset(self) -> None:
        """Clear error state so the worker can accept new work."""
        self._error = None

    # ── Event log ─────────────────────────────────────────────────────────

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
