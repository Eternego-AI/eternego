"""Persona — closing the day: settle cognition, archive, grow, write diary, re-wake."""

import json

from application.business.outcome import Outcome
from application.core import bus, models, paths
from application.core.brain.pulse import Phase, Pulse
from application.platform import datetimes, filesystem, logger
from application.platform.asyncio_worker import Worker

from .grow import grow
from .wake import wake
from .write_diary import write_diary


async def sleep(ego, living) -> Outcome[None]:
    """Close the day and open the next morning.

    Flip the phase to night, nudge the worker so the night-phase cycle runs
    (reflect consolidates, archive walks the day's residue), settle, then do
    the sleep work (archive conversation to history, grow if running locally,
    write diary). After the work, clear the archive, stop the old worker, swap
    a fresh Pulse onto Living, and wake into the new morning."""
    persona = ego.persona
    bus.propose("Sleeping", {"persona": persona})
    logger.info("Sleeping", {"persona": persona})

    living.pulse.phase = Phase.NIGHT
    living.pulse.worker.nudge()
    await living.pulse.worker.settle()

    try:
        conversation = paths.read_jsonl(paths.conversation(persona.id))
        if conversation:
            lines = [f"[{e.get('time', '')}] {e['role']}: {e['content']}" for e in conversation]
            filename = paths.add_history_entry(persona.id, "conversation", "\n".join(lines))
            paths.append_line(
                paths.history_briefing(persona.id),
                f"- {datetimes.iso_8601(datetimes.now())}: {filename}",
            )
            filesystem.write(paths.conversation(persona.id), "")

        if models.is_local(persona.thinking):
            grow_outcome = await grow(persona)
            if not grow_outcome.success:
                logger.warning("Growing on sleep failed", {"persona": persona, "error": grow_outcome.message})

        diary_outcome = await write_diary(persona)
        if not diary_outcome.success:
            logger.error("Writing diary on sleep failed", {"persona": persona, "error": diary_outcome.message})

        ego.memory.clear_archive()
        living.signals.clear()

        # Strip the heavy per-minute `signals` field from older health-log
        # entries so the file stays small across days. The day's detail
        # lives until the next sleep; what remains in the log afterward
        # is just the lightweight tick metadata (time, fault counts,
        # providers) that drives the uptime grid.
        try:
            health_path = paths.health_log(persona.id)
            if health_path.exists():
                entries = paths.read_jsonl(health_path)
                slim = "\n".join(
                    json.dumps({k: v for k, v in e.items() if k != "signals"})
                    for e in entries
                )
                if slim:
                    slim += "\n"
                filesystem.write(health_path, slim)
        except Exception as e:
            logger.warning("Trimming health log signals on sleep failed",
                           {"persona": persona, "error": str(e)})

        await living.pulse.worker.stop()

        living.pulse = Pulse(Worker())

        await wake(ego, living)

        bus.broadcast("Persona asleep", {"persona": persona})
        return Outcome(success=True, message="Sleep complete.")

    except Exception as e:
        bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Sleep failed unexpectedly.")
