"""Pulse — the rhythm of being-alive.

Carries the phase of the day (morning / day / night), the worker that
performs the work of each beat, and the felt stream of signals that
record what happened when. Pulse is the time axis of the architecture:
phase, history of activity, and the worker that turns time into action
all live here.

The phase is set by the callers that transition it — wake flips it to
morning, a first-message in hear/see flips it to day, sleep flips it
to night.

`Phase.hint()` returns the phase-specific system prompt appended after
ego.identity on each model call. Phase changes are rare and immediately
trigger persona activity, so cache invalidation on the appended block is
a non-issue. `Pulse.hint()` delegates and handles the unset case.

`Pulse.is_idle(seconds=None)` reports whether real activity (a
CapabilityRun signal) has been absent for the given window. Sleeps the
remainder when the window hasn't elapsed yet, returning False if a nudge
fires during the wait.
"""
import time
from enum import Enum

from application.core.brain.signals import CapabilityRun
from application.core.data import Persona, Prompt
from application.platform.asyncio_worker import Worker
from application.platform.observer import Signal, subscribe, unsubscribe


class Phase(Enum):
    MORNING = "morning"
    DAY = "day"
    NIGHT = "night"

    def hint(self) -> list[Prompt]:
        match self:
            case Phase.MORNING:
                text = "This is morning time for you. Fresh start, a day ahead — plan what you see actionable in your context to be productive."
            case Phase.DAY:
                text = "This is day. You know what to do; live it the most efficient."
            case Phase.NIGHT:
                text = "This is night. A plan for following what you are doing should be on your context; what should get done next should be on your context."
        return [Prompt(role="system", content=text)]


class Pulse:
    worker: Worker

    def __init__(self, worker: Worker, persona: Persona):
        self.worker = worker
        self.persona = persona
        self.phase: Phase | None = None
        self.signals: list[Signal] = []
        self.created_at: int = time.time_ns()
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

    def hint(self) -> list[Prompt]:
        return self.phase.hint() if self.phase else []

    async def is_idle(self, seconds: int | None = None) -> bool:
        """True if no real conversation activity in the given window.

        If `seconds` is omitted, reads `self.persona.idle_timeout`. If the
        last activity is already older than that, returns True immediately.
        Otherwise sleeps the remaining time via `worker.can_sleep` and returns
        True if the wait completed uninterrupted, or False if a nudge fired
        during the wait (activity arrived).

        Activity is a CapabilityRun signal (tool/ability fired by Clock's
        executor). Routine cycle ticks/tocks and heartbeat noise don't count.
        If no activity has been captured yet (fresh restart), the pulse's
        birth time is the reference."""
        if seconds is None:
            seconds = self.persona.idle_timeout
        latest = self.created_at
        for signal in reversed(self.signals):
            if isinstance(signal, CapabilityRun):
                latest = signal.time
                break
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
