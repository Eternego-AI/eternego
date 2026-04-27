"""Persona — opening the morning: flip the phase, start the clock."""

from application.business.outcome import Outcome
from application.core import bus
from application.core.brain import clock
from application.core.brain.pulse import Phase
from application.platform import logger


async def wake(ego, living) -> Outcome[None]:
    """Enter morning and begin ticking.

    Called at startup by the agent and at the end of sleep by the sleep spec
    (after the pulse has been replaced). Flips the phase to morning and hands
    the worker the Living's cycle to run."""
    persona = ego.persona
    bus.propose("Waking", {"persona": persona})
    logger.info("Waking", {"persona": persona})

    living.pulse.phase = Phase.MORNING
    living.pulse.worker.run(clock.run, living)

    bus.broadcast("Awake", {"persona": persona})
    return Outcome(success=True, message="")
