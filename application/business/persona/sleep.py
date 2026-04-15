"""Persona — end-of-shift ritual: archive the day, grow from it, write diary."""

from application.business.outcome import Outcome
from application.core import bus, models, paths
from application.core.data import Persona
from application.platform import datetimes, filesystem, logger

from .grow import grow
from .write_diary import write_diary


async def sleep(persona: Persona) -> Outcome[None]:
    """Close the day: archive conversation, grow from it (if local), write diary."""
    await bus.propose("Sleeping", {"persona": persona})

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

        await bus.broadcast("Persona asleep", {"persona": persona})
        return Outcome(success=True, message="Sleep complete.")

    except Exception as e:
        await bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Sleep failed unexpectedly.")
