"""Ego — runtime state for a served persona (the persona's current mind)."""

from application.core.brain import character, functions, situation
from application.core.brain.mind.memory import Memory
from application.core import paths
from application.core.data import Message, Persona, Prompt
from application.platform import datetimes, logger


class Ego:
    """The current mind of a served persona.

    Attached to persona.ego while served; None when dormant. Holds memory,
    worker, and current situation. Exposes behaviors (receive, identity,
    consciousness, settle, stop, persist, is_sleeping) without leaking
    internals.
    """

    def __init__(self, p: Persona, worker, situation=None):
        self.persona = p
        self.worker = worker
        self.memory = Memory(p)
        self.memory.remember()
        self.current_situation = situation
        self.channels: list = []

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

    def persist(self) -> None:
        """Save memory to disk."""
        logger.info("Persisting memory", {"persona": self.persona})
        self.memory.persist()

    def is_sleeping(self) -> bool:
        """Return True if the ego is in the sleep situation."""
        return self.current_situation is situation.sleep

    def receive(self, message: Message) -> None:
        """Ingest a person's message — log the words to conversation, mark the experience in memory."""
        entry = {
            "role": "person",
            "content": message.content,
            "channel": message.channel.type if message.channel else "",
            "time": datetimes.iso_8601(datetimes.now()),
        }
        if message.media:
            entry["media"] = {"source": message.media.source, "query": message.media.query}
        paths.append_jsonl(paths.conversation(self.persona.id), entry)
        if not message.media:
            message.prompt = Prompt(role="user", content=f"The person said: {message.content}")
        self.memory.add(message)
        self.current_situation = situation.normal
        self.worker.nudge()

    def identity(self) -> str:
        """Return assembled identity text in onion order: character → situation → ego."""
        sections = [character.shape(self.persona)]

        if self.current_situation:
            situation_text = self.current_situation(self.persona.id)
            if situation_text:
                sections.append(situation_text)

        ego = []
        person_id = paths.read(paths.person_identity(self.persona.id))
        if person_id.strip():
            ego.append("## The Person\n\n" + person_id.strip())

        traits = paths.read(paths.person_traits(self.persona.id))
        if traits.strip():
            ego.append("## The Person's Traits\n\n" + traits.strip())

        wishes = paths.read(paths.wishes(self.persona.id))
        if wishes.strip():
            ego.append("## What They Wish For\n\n" + wishes.strip())

        struggles = paths.read(paths.struggles(self.persona.id))
        if struggles.strip():
            ego.append("## What Stands in Their Way\n\n" + struggles.strip())

        persona_trait = paths.read(paths.persona_trait(self.persona.id))
        if persona_trait.strip():
            ego.append("## Your Personality With Them\n\n" + persona_trait.strip())

        if self.memory.context:
            ego.append("## Recent Context\n\n" + self.memory.context.strip())

        if ego:
            sections.append("# What You Know\n\n" + "\n\n".join(ego))

        return "\n\n".join(sections)
