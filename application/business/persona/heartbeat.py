"""Persona — one heartbeat tick: check health, trigger routines."""

from application.business.outcome import Outcome
from application.business.routine.trigger import trigger
from application.core import bus
from application.platform import datetimes

from .health_check import health_check


async def heartbeat(ego, living, sleep_fn=None) -> Outcome[None]:
    """One heartbeat tick — check health, fire due routines."""
    bus.propose("Heartbeat", {"persona": ego.persona})
    await health_check(ego, living, datetimes.now())
    await trigger(ego.persona, sleep_fn)
    bus.broadcast("Heartbeat complete", {"persona": ego.persona})
    return Outcome(success=True, message="")
