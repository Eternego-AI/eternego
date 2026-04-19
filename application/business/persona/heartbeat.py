"""Persona — one heartbeat tick: self-check health."""

from application.business.outcome import Outcome
from application.core import bus
from application.core.data import Persona
from application.platform import datetimes

from .health_check import health_check


async def heartbeat(persona: Persona) -> Outcome[None]:
    """One heartbeat tick — check health."""
    bus.propose("Heartbeat", {"persona": persona})
    await health_check(persona, datetimes.now())
    bus.broadcast("Heartbeat complete", {"persona": persona})
    return Outcome(success=True, message="")
