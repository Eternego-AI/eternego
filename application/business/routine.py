"""Routine — recurring spec triggers for each persona."""
from application.core.data import Persona
from application.platform import logger, datetimes, filesystem, processes
from application.core import bus, paths
from application.business import persona as persona_spec
from application.business.outcome import Outcome


async def trigger(persona: Persona) -> Outcome[dict]:
    """Fire all routine entries whose trigger time matches the current minute."""
    await bus.propose("Triggering routines", {"persona": persona})
    current_time = datetimes.now().strftime("%H:%M")
    fired = []

    path = paths.routines(persona.id)
    data = filesystem.read_json(path) if path.exists() else {}
    for entry in data.get("routines", []):
        spec = entry.get("spec", "")
        time = entry.get("time", "")
        if time != current_time:
            continue
        spec_fn = getattr(persona_spec, spec, None)
        if not spec_fn:
            logger.warning("Unknown routine spec", {"spec": spec, "persona_id": persona.id})
            continue
        logger.info("Triggering routine", {"spec": spec, "persona_id": persona.id})
        processes.run_async(lambda fn=spec_fn: fn(persona))
        fired.append(spec)

    await bus.broadcast("Routines triggered", {"persona": persona, "fired": fired})
    return Outcome(success=True, message=f"Routines checked. Fired: {fired or 'none'}")
