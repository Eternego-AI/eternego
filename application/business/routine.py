"""Routine — recurring spec triggers for each persona."""
from application.core.data import Persona
from application.platform import logger, datetimes, filesystem, processes
from application.core import bus, paths
from application.business import persona as persona_spec
from application.business.outcome import Outcome


async def trigger(persona: Persona) -> Outcome[dict]:
    """Fire all routine entries whose trigger time matches the current minute."""
    await bus.propose("Triggering routines", {"persona": persona})
    now_utc = datetimes.now()
    current_time = now_utc.strftime("%H:%M")
    fired = []

    path = paths.routines(persona.id)
    data = filesystem.read_json(path) if path.exists() else {}
    for entry in data.get("routines", []):
        spec = entry.get("spec", "")
        time = entry.get("time", "")
        tz_name = entry.get("timezone")
        if tz_name:
            try:
                utc_dt = datetimes.to_utc(f"{now_utc.strftime('%Y-%m-%d')} {time}", tz_name)
                trigger_time = utc_dt.strftime("%H:%M")
            except Exception:
                logger.warning("Invalid timezone in routine", {"spec": spec, "timezone": tz_name, "persona_id": persona.id})
                continue
        else:
            trigger_time = time
        if trigger_time != current_time:
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
