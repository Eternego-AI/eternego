"""Heart — the persona's periodic heartbeat: routines and destiny checks."""

from application.business import persona, routine
from application.core.data import Persona
from application.platform import datetimes, logger


async def beat(agent: Persona) -> None:
    """One heartbeat cycle for a persona."""
    now = datetimes.now()
    logger.info("Heartbeat", {"persona": agent.id, "time": now.strftime("%Y-%m-%d %H:%M")})

    await persona.live(agent, now)
    await routine.trigger(agent)

