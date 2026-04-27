"""Pulse — the rhythm of being-alive.

Carries the phase of the day (morning / day / night) and the worker that
performs the work of each beat. The phase is set by the callers that
transition it — wake flips it to morning, a first-message in hear/see
flips it to day, sleep flips it to night.

Cognitive activity history (faults, events, beat counts) lives on
living.signals now — Pulse stays focused on rhythm and the executor.

`Phase.hint()` returns the phase-specific system prompt appended after
ego.identity on each model call. Phase changes are rare and immediately
trigger persona activity, so cache invalidation on the appended block is
a non-issue. `Pulse.hint()` delegates and handles the unset case.
"""
from enum import Enum

from application.core.data import Prompt
from application.platform.asyncio_worker import Worker


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

    def __init__(self, worker: Worker):
        self.worker = worker
        self.phase: Phase | None = None

    def hint(self) -> list[Prompt]:
        return self.phase.hint() if self.phase else []
