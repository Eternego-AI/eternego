"""Observations — applying what the persona observed."""

from application.platform import logger
from application.core import person, agent
from application.core.data import Observation, Persona


async def effect(persona: Persona, observation: Observation) -> None:
    """Apply observations to the persona — facts, traits, and context."""
    logger.info("Applying observations", {"persona_id": persona.id})
    await person.add_facts(persona, observation.facts)
    await person.add_traits(persona, observation.traits)
    await agent.learn(persona, observation.context)
