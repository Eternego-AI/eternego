"""Persona — waking a persona and opening gateways."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents, bus
from application.core.brain import situation
from application.core.data import Persona

from .connect import connect


@dataclass
class WakeData:
    persona: Persona


async def wake(persona: Persona, worker) -> Outcome[WakeData]:
    """Wake a persona — open gateways, construct ego, register."""
    await bus.propose("Waking persona", {"persona": persona})

    if not (persona.channels or []):
        await bus.broadcast("Wake failed", {"persona": persona, "reason": "no_channels"})
        return Outcome(success=False, message="No channels configured for this persona.")

    for channel in (persona.channels or []):
        outcome = await connect(persona, channel)
        if not outcome.success:
            await bus.broadcast("Wake failed", {"persona": persona, "error": outcome.message})
            return outcome

    ego = agents.Ego(persona, worker, situation.wake)
    agents.register(persona, ego)

    await bus.broadcast("Persona awake", {"persona": persona})
    return Outcome(success=True, message="Persona awake", data=WakeData(persona=persona))
