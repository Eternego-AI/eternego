"""Pulse — the rhythm of being-alive.

Carries the phase of the day (morning / day / night), the worker that
performs the work of each beat, and the felt stream of signals that
record what happened when. Pulse is the time axis of the architecture:
phase, history of activity, and the worker that turns time into action
all live here.

The phase is set by the callers that transition it — wake flips it to
morning, a first-message in hear/see flips it to day, sleep flips it
to night.

`Pulse.is_idle(seconds=None)` reports whether real activity (a
CapabilityRun signal) has been absent for the given window. Sleeps the
remainder when the window hasn't elapsed yet, returning False if a nudge
fires during the wait.
"""
import time
from enum import Enum

from application.core.brain.signals import CapabilityRun
from application.core.data import Persona
from application.platform.asyncio_worker import Worker
from application.platform.observer import Signal, subscribe, unsubscribe


class Phase(Enum):
    MORNING = "morning"
    DAY = "day"
    NIGHT = "night"


class Pulse:
    worker: Worker

    def __init__(self, worker: Worker, persona: Persona):
        self.worker = worker
        self.persona = persona
        self.phase: Phase | None = None
        self.signals: list[Signal] = []
        self._subscribed = False
        self._on_construct()

    def _on_construct(self) -> None:
        """Construction hook. Default: subscribe to the bus so the persona's
        signal stream populates `self.signals`. Subclasses override to
        skip (PastPulse does)."""
        subscribe(self._on_signal)
        self._subscribed = True

    async def _on_signal(self, signal: Signal) -> None:
        """Capture signals dispatched on this persona's behalf into the felt
        stream. Filters by persona id so multi-persona daemons don't cross
        their streams."""
        details = signal.details if isinstance(signal.details, dict) else {}
        p = details.get("persona")
        signal_pid = getattr(p, "id", None) if p is not None else None
        if signal_pid == self.persona.id:
            self.signals.append(signal)

    async def is_idle(self, seconds: int | None = None) -> bool:
        """True if no real conversation activity in the current phase's window.

        Activity is a CapabilityRun signal (tool/ability fired by Clock's
        executor). Routine cycle ticks/tocks and heartbeat noise don't count.
        Signals reset on every phase transition (`Living.phase()`), so the
        latest CapabilityRun in `self.signals` is necessarily the last one
        in the current phase.

        - No CapabilityRun in this phase yet → wait the full window via
          `worker.can_sleep`. True if uninterrupted (window elapsed without
          activity → idle); False if a nudge fires during the wait.
        - Latest CapabilityRun older than `seconds` (default
          `persona.idle_timeout`) → return True immediately.
        - Otherwise sleep the remaining time via `worker.can_sleep` and
          return True if uninterrupted, False if a nudge fires (activity
          arrived).

        Returning False without waiting would create a tight loop with
        reflect (raises ReflectInterrupted → clock restarts cycle → reflect
        runs again → raises again, with no chance for a nudge to land)."""
        if seconds is None:
            seconds = self.persona.idle_timeout
        latest = None
        for signal in reversed(self.signals):
            if isinstance(signal, CapabilityRun):
                latest = signal.time
                break
        if latest is None:
            return await self.worker.can_sleep(seconds)
        elapsed_ns = time.time_ns() - latest
        if elapsed_ns >= seconds * 1_000_000_000:
            return True
        remaining = seconds - elapsed_ns / 1_000_000_000
        return await self.worker.can_sleep(remaining)

    def dispose(self) -> None:
        """Tear down. Unsubscribes from the bus so signals stop landing on a
        Pulse that is no longer running."""
        if self._subscribed:
            unsubscribe(self._on_signal)
            self._subscribed = False
