"""Ego — runtime state for a served persona (the persona's current mind)."""

from application.core.brain import functions, identities, situation
from application.core.brain.mind import clock
from application.core.brain.mind.memory import Memory
from application.core.brain.mind.pulse import Pulse
from application.core import paths
from application.core.data import Message, Persona, Prompt
from application.platform import datetimes, logger
from application.platform.asyncio_worker import Worker


class Ego:
    """The current mind of a served persona.

    Owned by the agent on shift (`agent.ego`). Created fresh each time manager
    serves the persona; released when the agent tears down. Holds memory and
    pulse; carries `self.persona` as a back-reference for config access.

    The pulse wraps the platform worker with the brain's situation (wake,
    normal, sleep). Tick reads the situation to decide whether to run the
    subconscious after conscious settles.
    """

    def __init__(self, p: Persona, worker):
        self.persona = p
        self.pulse = Pulse(worker)
        self.memory = Memory(p)

    def consciousness(self) -> list:
        """Build the conscious brain function sequence as (name, zero-arg async callable) pairs.
        Names are what tick writes into the worker's event log so health_check knows
        which cognitive step succeeded or faulted."""
        return [
            ("realize",    lambda: functions.realize(self, self.perspective(), self.memory)),
            ("recognize",  lambda: functions.recognize(self, self.personality(), self.memory)),
            ("wondering",  lambda: functions.wondering(self, self.teacher(), self.memory)),
            ("decide",     lambda: functions.decide(self, self.personality(), self.memory)),
            ("experience", lambda: functions.experience(self, self.personality(), self.memory)),
            ("reflect",    lambda: functions.reflect(self, self.personality(), self.memory)),
        ]

    def subconsciousness(self) -> list:
        """Build the subconscious brain function sequence — runs after conscious settles.
        Archive and transform work on archived conversation batches, not live messages."""
        return [
            ("archive",    lambda: functions.archive(self, self.personality(), self.memory)),
            ("transform",  lambda: functions.transform(self, self.personality(), self.memory)),
        ]

    def wake(self) -> None:
        """Set situation to wake, remember the wake message, start the clock."""
        logger.info("Waking", {"persona": self.persona})
        self.pulse.situation = situation.wake
        self.memory.remember(Message(
            content="wake up",
            prompt=Prompt(role="user", content="wake up"),
        ))
        self.pulse.worker.run(clock.tick, self.consciousness(), self.subconsciousness(), self.pulse)

    async def sleep_cycle(self, sleep_spec) -> None:
        """Full sleep cycle: settle, run sleep spec, clear archive, restart with fresh worker."""
        logger.info("Sleeping", {"persona": self.persona})
        self.pulse.situation = situation.sleep
        self.memory.remember(Message(
            content="go to sleep",
            prompt=Prompt(role="user", content="go to sleep"),
        ))
        self.pulse.worker.nudge()
        await self.pulse.worker.settle()
        await sleep_spec(self)
        self.memory.clear_archive()
        await self.pulse.worker.stop()
        self.pulse = Pulse(Worker())
        self.wake()


    def receive(self, message: Message) -> None:
        """Ingest a person's message — log the words to conversation, mark the experience in memory."""
        entry = {
            "role": "person",
            "content": message.content,
            "channel": {"type": message.channel.type, "name": message.channel.name or ""} if message.channel else None,
            "time": datetimes.iso_8601(datetimes.now()),
        }
        if message.media:
            entry["media"] = {"source": message.media.source, "caption": message.media.caption}
        paths.append_jsonl(paths.conversation(self.persona.id), entry)
        if not message.media:
            message.prompt = Prompt(role="user", content=message.content)
        self.memory.remember(message)
        self.pulse.situation = situation.normal
        self.pulse.worker.nudge()

    def personality(self) -> str:
        """The persona's own voice — character, situation, person facts, carried context."""
        return identities.personality(self.persona, self.pulse.situation, self.memory.context)

    def perspective(self) -> str:
        """A neutral observer's voice — reads the persona's conversation from outside."""
        return identities.perspective(self.persona)

    def teacher(self) -> str:
        """An architect's voice — writes new abilities for the persona."""
        return identities.teacher(self.persona)
