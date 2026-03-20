"""Agents — persona lifecycle management and runtime state."""

import asyncio
import secrets

from datetime import timedelta

from application.core.brain.data import Signal, Perception, Thought
from application.core.brain.mind.memory import Memory
from application.core.brain.mind import meanings
from application.core import paths
from application.core.data import Persona, Channel
from application.core.exceptions import MindError, AgentError
from application.platform import datetimes, logger

_personas: dict[str, "Agent"] = {}


def register(p: Persona) -> None:
    """Register a persona in the runtime state."""
    logger.info("Registering agent", {"persona": p})
    _personas[p.id] = Agent(p)


def personas() -> list[Persona]:
    """Return all currently running personas."""
    return [a.persona for a in _personas.values()]


def find(persona_id: str) -> Persona:
    """Return the running Persona by id. Raises MindError if not registered."""
    agent = _personas.get(persona_id)
    if agent is None:
        raise MindError(f"Persona '{persona_id}' is not running.")
    return agent.persona


def persona(p: Persona) -> "Agent":
    """Return the agent for this persona."""
    agent = _personas.get(p.id)
    if agent is None:
        raise MindError(f"Agent not registered: {p.id}")
    return agent


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


class Agent:
    """Runtime state and operations for a running persona."""

    def __init__(self, p: Persona):
        self.persona = p
        self.memory: Memory | None = None
        self.gateways: list = []
        self.pairing_codes: dict = {}
        self.tick_task: asyncio.Task | None = None
        self.blocked: bool = False

    @property
    def _mem(self) -> Memory:
        if self.memory is None:
            raise MindError(f"Mind not loaded for persona {self.persona.id}")
        return self.memory

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def load_mind(self) -> None:
        """Load meanings, construct memory, and restore from disk."""
        logger.info("Loading mind", {"persona": self.persona})
        all_meanings = meanings.built_in(self.persona) + meanings.specific_to(self.persona)
        self.memory = Memory(self.persona, all_meanings)
        self.memory.remember()

    def start(self) -> None:
        """Start the thinking tick loop."""
        logger.info("Starting agent", {"persona": self.persona})
        from application.core.brain.mind import clock

        self.tick_task = asyncio.create_task(clock.tick(self._mem))

    async def stop(self, force: bool = False) -> None:
        """Block new signals, stop the tick loop. Force skips waiting for the mind to settle."""
        logger.info("Stopping agent", {"persona": self.persona, "force": force})
        self.blocked = True

        if not force and self.memory:
            while not self.memory.settled:
                await asyncio.sleep(0.05)

        if self.tick_task and not self.tick_task.done():
            self.tick_task.cancel()
            try:
                await self.tick_task
            except (asyncio.CancelledError, Exception):
                pass
        self.tick_task = None

    def unload(self) -> None:
        """Persist memory and unregister."""
        logger.info("Unloading agent", {"persona": self.persona})
        if self.memory:
            self.memory.persist()
        _personas.pop(self.persona.id, None)

    # ── Signals ──────────────────────────────────────────────────────────────

    def trigger(self, signal: Signal) -> None:
        """Accept an outside signal. Ignored when blocked."""
        logger.info("Trigger signal", {"persona": self.persona, "signal": signal})
        if self.blocked:
            logger.warning("Signal ignored, agent is blocked", {"persona": self.persona, "signal": signal})
            return
        self._mem.trigger(signal)

    def incept(self, perception: Perception) -> None:
        """Inject a perception directly, bypassing understanding."""
        logger.info("Incept perception", {"persona": self.persona, "perception": perception})
        self._mem.incept(perception)

    def question(self, thought: Thought) -> None:
        """Inject a pre-formed thought, bypassing understanding and recognition."""
        logger.info("Question", {"persona": self.persona, "thought": thought})
        self._mem.incept(thought.perception)
        self._mem.question(thought)

    def read(self) -> list[Signal]:
        """Return all signals in the mind sorted by creation time."""
        logger.info("Read signals", {"persona": self.persona})
        return sorted(self._mem.signals, key=lambda s: s.created_at)

    # ── Learning ─────────────────────────────────────────────────────────────

    async def learn(self, conversations: str) -> None:
        """Run subconscious knowledge extraction on the given conversations."""
        logger.info("Learn", {"persona": self.persona})
        from application.core.brain.mind import subconscious as sub

        if not conversations:
            logger.warning("No conversations to learn from", {"persona": self.persona})
            return

        await sub.person_identity(self.persona, conversations)
        await sub.person_traits(self.persona, conversations)
        await sub.wishes(self.persona, conversations)
        await sub.struggles(self.persona, conversations)
        await sub.persona_context(self.persona, conversations)
        await sub.synthesize_dna(self.persona)

    async def learn_from_experience(self) -> None:
        """Learn from all thoughts, then archive each individually."""
        logger.info("Learn from experience", {"persona": self.persona})
        from application.core.brain import perceptions

        mem = self._mem

        all_thoughts = list(mem.intentions)
        if not all_thoughts:
            return

        conversations = []
        for thought in all_thoughts:
            conversations.append(perceptions.thread(thought.perception))

        await self.learn("\n\n---\n\n".join(conversations))

        for thought in all_thoughts:
            from application.core.brain.data import SignalEvent
            summaries = [s for s in thought.perception.thread if s.event == SignalEvent.summarized]
            recap = summaries[-1].content if summaries else None

            filename = mem.archive(thought)

            if recap:
                paths.add_history_briefing(self.persona.id, "| File | Recap |", f"| {filename} | {recap} |")
