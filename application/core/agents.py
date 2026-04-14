"""Agents — persona lifecycle management and runtime state."""

import secrets

from datetime import timedelta

from application.core.brain import character, functions
from application.core.brain.mind.memory import Memory
from application.core import paths
from application.core.data import Persona, Channel
from application.core.exceptions import MindError, AgentError
from application.platform import datetimes, logger

_personas: dict[str, "Ego"] = {}


def register(p: Persona, ego: "Ego") -> None:
    """Store a constructed ego and start the tick."""
    logger.info("Registering agent", {"persona": p})
    _personas[p.id] = ego
    from application.core.brain.mind import clock
    ego.worker.run(clock.tick, ego.consciousness(), ego.worker)


def personas() -> list[Persona]:
    """Return all currently running personas."""
    return [a.persona for a in _personas.values()]


def find(persona_id: str) -> Persona:
    """Return the running Persona by id. Raises MindError if not registered."""
    agent = _personas.get(persona_id)
    if agent is None:
        raise MindError(f"Persona '{persona_id}' is not running.")
    return agent.persona


def persona(p: Persona) -> "Ego":
    """Return the ego for this persona."""
    ego = _personas.get(p.id)
    if ego is None:
        raise MindError(f"Ego not registered: {p.id}")
    return ego


def pair(p: Persona, channel: Channel) -> str:
    """Generate a pairing code unique across all personas, store it on the agent."""
    logger.info("Generating pairing code", {"persona": p, "channel": channel})
    agent = persona(p)
    while True:
        code = secrets.token_hex(3).upper()
        taken = False
        for a in _personas.values():
            if code in a.pairing_codes:
                taken = True
                break
        if not taken:
            break
    agent.pairing_codes[code] = {
        "channel_type": channel.type,
        "channel_name": channel.name,
        "created_at": datetimes.now(),
    }
    return code


def take_code(code: str) -> tuple[Persona, str, str]:
    """Claim a pairing code and return (persona, channel_type, channel_name).

    Raises AgentError if the code is invalid or expired.
    """
    logger.info("Taking pairing code", {"code": code})
    code = code.upper()
    for a in _personas.values():
        entry = a.pairing_codes.get(code)
        if entry is None:
            continue
        if datetimes.now() - entry["created_at"] > timedelta(minutes=10):
            a.pairing_codes.pop(code, None)
            raise AgentError("Pairing code has expired. Ask the persona to send a new message to get a fresh code.")
        a.pairing_codes.pop(code, None)
        return a.persona, entry["channel_type"], entry["channel_name"]
    raise AgentError("Pairing code is invalid or has expired.")


class Ego:
    """Runtime state for a running persona."""

    def __init__(self, p: Persona, worker, situation=None):
        self.persona = p
        self.worker = worker
        self.memory = Memory(p)
        self.memory.remember()
        self.pairing_codes: dict = {}
        self.current_situation = situation

    def consciousness(self) -> list:
        """Build the brain function sequence as a list of zero-arg async callables."""
        return [
            lambda: functions.realize(self.persona, self.identity(), self.memory),
            lambda: functions.recognize(self.persona, self.identity(), self.memory),
            lambda: functions.decide(self.persona, self.identity(), self.memory),
            lambda: functions.experience(self.persona, self.identity(), self.memory),
            lambda: functions.transform(self.persona, self.identity(), self.memory),
            lambda: functions.reflect(self.persona, self.identity(), self.memory),
        ]

    async def settle(self) -> None:
        """Nudge the tick and wait for it to finish processing."""
        logger.info("Settling", {"persona": self.persona})
        self.worker.nudge()
        await self.worker.settle()

    async def stop(self) -> None:
        """Stop the worker — tick exits cooperatively."""
        logger.info("Stopping", {"persona": self.persona})
        await self.worker.stop()

    def unload(self) -> None:
        """Persist memory and unregister."""
        logger.info("Unloading agent", {"persona": self.persona})
        self.memory.persist()
        _personas.pop(self.persona.id, None)

    def identity(self) -> str:
        """Return assembled identity text: character, knowledge, and situation."""
        sections = [character.shape(self.persona)]

        if self.current_situation:
            sections.append(self.current_situation(self.persona.id))

        wishes = paths.read(paths.wishes(self.persona.id))
        if wishes.strip():
            sections.append(
                "# What the Person Wants\n"
                + wishes.strip()
            )

        struggles = paths.read(paths.struggles(self.persona.id))
        if struggles.strip():
            sections.append(
                "# What the Person Struggles With\n"
                + struggles.strip()
            )

        traits = paths.read(paths.person_traits(self.persona.id))
        if traits.strip():
            sections.append(
                "# The Person's Traits\n"
                + traits.strip()
            )

        if self.memory.context:
            sections.append(
                "# Recent Context\n"
                + self.memory.context.strip()
            )

        return "\n\n".join(sections)
