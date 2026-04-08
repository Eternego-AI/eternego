"""Persona — waking a persona and opening gateways."""

from application.business.outcome import Outcome
from application.core import agents, bus
from application.core.brain import situation
from application.core.brain.mind import meanings

from .connect import connect
from .find import find


async def wake(persona_id: str, worker) -> Outcome[dict]:
    """Wake a persona — find, open gateways, construct ego, register."""
    await bus.propose("Waking persona", {"persona_id": persona_id})

    outcome = await find(persona_id)
    if not outcome.success:
        await bus.broadcast("Wake failed", {"persona_id": persona_id, "reason": "not_found"})
        return outcome

    agent = outcome.data["persona"]

    if not (agent.channels or []):
        await bus.broadcast("Wake failed", {"persona": agent, "reason": "no_channels"})
        return Outcome(success=False, message="No channels configured for this persona.")

    for channel in (agent.channels or []):
        outcome = await connect(agent, channel)
        if not outcome.success:
            await bus.broadcast("Wake failed", {"persona": agent, "error": outcome.message})
            return outcome

    all_meanings = meanings.built_in(agent) + meanings.specific_to(agent)
    ego = agents.Ego(agent, all_meanings, worker, situation.wake)
    agents.register(agent, ego)

    await bus.broadcast("Persona awake", {"persona": agent})
    return Outcome(success=True, message="Persona awake", data={"persona_id": agent.id})
