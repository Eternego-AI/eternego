"""Persona — listing currently running personas."""

from application.business.outcome import Outcome
from application.core import agents


async def running() -> Outcome[dict]:
    """Return all currently running personas."""
    return Outcome(success=True, message="", data={"personas": agents.personas()})
