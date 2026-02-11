"""Frontier — escalation to a more powerful external model."""

from application.platform import logger
from application.core import prompts
from application.core.data import Persona
from application.core import agent


async def allow_escalation(persona: Persona) -> None:
    """Enable escalation to the frontier model for this persona."""
    logger.info("Allowing escalation", {"persona_id": persona.id, "frontier": persona.frontier.name})
    escalation = prompts.ESCALATION.format(name=persona.frontier.name, provider=persona.frontier.provider)
    await agent.add_instruction(persona, "escalation", escalation)
