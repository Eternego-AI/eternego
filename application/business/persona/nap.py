"""Persona — quick stop and unload."""

from application.business.outcome import Outcome
from application.core import agents, bus, gateways
from application.core.data import Persona


async def nap(persona: Persona) -> Outcome[dict]:
    """Quick stop — clear gateways, force-stop thinking, unload."""
    await bus.propose("Napping", {"persona": persona})

    agent = agents.persona(persona)
    try:
        gateways.of(persona).clear()
        await agent.stop()
        agent.unload()

        await bus.broadcast("Persona napping", {"persona": persona})
        return Outcome(success=True, message="Nap complete.")

    except Exception as e:
        agent.unload()
        await bus.broadcast("Nap failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Nap failed unexpectedly.")
