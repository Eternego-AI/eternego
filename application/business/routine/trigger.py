"""Routine — firing scheduled agent behaviors when their time comes."""

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Persona
from application.platform import logger, datetimes, filesystem, processes


async def trigger(persona: Persona, sleep_by) -> Outcome[None]:
    """Fire scheduled behaviors due at the current minute.

    sleep_by: callable the agent provides — invoked if a sleep routine is due.
    """
    bus.propose("Triggering routines", {"persona": persona})
    current_time = datetimes.now().strftime("%H:%M")
    fired = []

    path = paths.routines(persona.id)
    data = filesystem.read_json(path) if path.exists() else {}
    for entry in data.get("routines", []):
        if entry.get("time") != current_time:
            continue
        name = entry.get("spec", "")
        if name == "sleep":
            logger.info("Triggering sleep", {"persona": persona})
            processes.run_async(sleep_by)
            fired.append("sleep")

    bus.broadcast("Routines triggered", {"persona": persona, "fired": fired})
    return Outcome(success=True, message=f"Routines checked. Fired: {fired or 'none'}")
