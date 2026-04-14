"""Persona — putting a persona to sleep for learning and growth."""

from application.business.outcome import Outcome
from application.core import agents, bus, gateways, models, paths
from application.core.brain import situation
from application.core.data import Persona
from application.core.exceptions import DNAError, EngineConnectionError
from application.platform import datetimes, filesystem, logger

from .grow import grow
from .wake import wake
from .write_diary import write_diary


async def sleep(persona: Persona) -> Outcome[None]:
    """Put a persona to sleep — settle, archive conversation, grow, write diary, then wake refreshed."""
    await bus.propose("Sleeping", {"persona": persona})

    agent = agents.persona(persona)
    worker = agent.worker
    try:
        agent.current_situation = situation.sleep
        await agent.settle()

        conversation = paths.read_jsonl(paths.conversation(persona.id))
        if conversation:
            lines = []
            for entry in conversation:
                lines.append(f"[{entry.get('time', '')}] {entry['role']}: {entry['content']}")
            filename = paths.add_history_entry(persona.id, "conversation", "\n".join(lines))
            paths.append_line(paths.history_briefing(persona.id),
                              f"- {datetimes.iso_8601(datetimes.now())}: {filename}")
            filesystem.write(paths.conversation(persona.id), "")

        if models.is_local(persona.thinking):
            grow_outcome = await grow(persona)
            if not grow_outcome.success:
                logger.warning("Growing on sleep failed", {"persona": persona, "error": grow_outcome.message})

        outcome = await write_diary(persona)
        if not outcome.success:
            logger.error("Writing diary on sleep failed", {"persona": persona, "error": outcome.message})

        gateways.of(persona).clear()
        agent.unload()
        await wake(persona, worker)

        await bus.broadcast("Persona asleep", {"persona": persona})
        return Outcome(success=True, message="Sleep complete.")

    except (DNAError, EngineConnectionError) as e:
        gateways.of(persona).clear()
        agent.unload()
        await wake(persona, worker)
        await bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
    except Exception as e:
        gateways.of(persona).clear()
        agent.unload()
        await wake(persona, worker)
        await bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Sleep failed unexpectedly.")
