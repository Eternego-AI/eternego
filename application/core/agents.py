"""Ego — runtime state for a served persona (the persona's current mind)."""

from application.core.brain import character, functions, situation
from application.core.brain.mind import clock
from application.core.brain.mind.memory import Memory
from application.core import paths
from application.core.data import Message, Persona, Prompt
from application.platform import datetimes, logger
from application.platform.asyncio_worker import Worker


class Ego:
    """The current mind of a served persona.

    Owned by the agent on shift (`agent.ego`). Created fresh each time manager
    serves the persona; released when the agent tears down. Holds memory,
    worker, and current situation; carries `self.persona` as a back-reference
    for config access. Exposes behaviors (receive, identity, consciousness,
    wake, sleep_cycle, settle, stop, is_sleeping) without leaking internals.
    """

    def __init__(self, p: Persona, worker, situation=None):
        self.persona = p
        self.worker = worker
        self.memory = Memory(p)
        self.current_situation = situation

    def consciousness(self) -> list:
        """Build the brain function sequence as (name, zero-arg async callable) pairs.
        Names are what tick writes into the worker's event log so health_check knows
        which cognitive step succeeded or faulted."""
        return [
            ("realize",    lambda: functions.realize(self, self.identity(), self.memory)),
            ("recognize",  lambda: functions.recognize(self, self.identity(), self.memory)),
            ("decide",     lambda: functions.decide(self, self.identity(), self.memory)),
            ("experience", lambda: functions.experience(self, self.identity(), self.memory)),
            ("transform",  lambda: functions.transform(self, self.identity(), self.memory)),
            ("reflect",    lambda: functions.reflect(self, self.identity(), self.memory)),
        ]

    def wake(self) -> None:
        """Set situation to wake, remember the wake message, start the clock."""
        logger.info("Waking", {"persona": self.persona})
        self.current_situation = situation.wake
        self.memory.remember(Message(
            content=f"Wake up {self.persona.name}",
            prompt=Prompt(role="user", content=f"Wake up {self.persona.name}"),
        ))
        self.worker.run(clock.tick, self.consciousness(), self.worker)

    async def sleep_cycle(self, sleep_spec) -> None:
        """Full sleep cycle: settle, run sleep spec, restart with fresh worker."""
        logger.info("Sleeping", {"persona": self.persona})
        self.current_situation = situation.sleep
        self.memory.remember(Message(
            content="Go to sleep",
            prompt=Prompt(role="user", content="Go to sleep"),
        ))
        await self.settle()
        await sleep_spec(self)
        await self.worker.stop()
        self.worker = Worker()
        self.wake()

    async def settle(self) -> None:
        """Nudge the tick and wait for it to finish processing."""
        logger.info("Settling", {"persona": self.persona})
        self.worker.nudge()
        await self.worker.settle()

    async def stop(self) -> None:
        """Stop the worker — tick exits cooperatively."""
        logger.info("Stopping", {"persona": self.persona})
        await self.worker.stop()

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
            entry["media"] = {"source": message.media.source, "caption": message.media.caption}
        paths.append_jsonl(paths.conversation(self.persona.id), entry)
        if not message.media:
            message.prompt = Prompt(role="user", content=f"The person said: {message.content}")
        self.memory.remember(message)
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
