"""Persona — listing currently running personas."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents


@dataclass
class RunningData:
    personas: list


async def running() -> Outcome[RunningData]:
    """Return all currently running personas."""
    return Outcome(success=True, message="", data=RunningData(personas=agents.personas()))
