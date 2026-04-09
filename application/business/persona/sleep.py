"""Persona — putting a persona to sleep for learning and growth."""

from application.business.outcome import Outcome
from application.core import agents, bus, gateways, models
from application.core.brain import situation
from application.core.data import Persona
from application.core.exceptions import DNAError, EngineConnectionError
from application.platform import logger

from .grow import grow
from .wake import wake
from .write_diary import write_diary


async def sleep(persona: Persona) -> Outcome[dict]:
    """Put a persona to sleep — learn from experience, grow, write diary, then wake refreshed."""
    await bus.propose("Sleeping", {"persona": persona})

    agent = agents.persona(persona)
    worker = agent.worker
    try:
        agent.current_situation = situation.sleep
        await agent.settle()

        await agent.learn_from_experience()

        if models.is_local(persona.thinking):
            grow_outcome = await grow(persona)
            if not grow_outcome.success:
                logger.warning("Growing on sleep failed", {"persona": persona, "error": grow_outcome.message})

        outcome = await write_diary(persona)
        if not outcome.success:
            logger.error("Writing diary on sleep failed", {"persona": persona, "error": outcome.message})

        gateways.of(persona).clear()
        agent.unload()
        await wake(persona.id, worker)

        await bus.broadcast("Persona asleep", {"persona": persona})
        return Outcome(success=True, message="Sleep complete.")

    except (DNAError, EngineConnectionError) as e:
        gateways.of(persona).clear()
        agent.unload()
        await wake(persona.id, worker)
        await bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
    except Exception as e:
        gateways.of(persona).clear()
        agent.unload()
        await wake(persona.id, worker)
        await bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Sleep failed unexpectedly.")
