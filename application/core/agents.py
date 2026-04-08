"""Agents — persona lifecycle management and runtime state."""

import secrets

from datetime import timedelta

from application.core.brain.data import Signal, Perception
from application.core.brain.mind.memory import Memory
from application.core.brain import character
from application.core import models, tools, paths
from application.core.data import Persona, Channel
from application.core.exceptions import MindError, AgentError
from application.platform import datetimes, logger

_personas: dict[str, "Ego"] = {}


def register(p: Persona, ego: "Ego") -> None:
    """Store a constructed ego and start the tick."""
    logger.info("Registering agent", {"persona": p})
    _personas[p.id] = ego
    from application.core.brain.mind import clock
    ego.worker.run(clock.tick, ego.consciousness(), ego.memory, ego.worker)


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
    """Runtime state, reasoning, and reply engine for a running persona."""

    def __init__(self, p: Persona, all_meanings: list, worker, situation=None):
        self.persona = p
        self.worker = worker
        self.meanings = all_meanings
        self.memory = Memory(p, all_meanings)
        self.memory.remember()
        self.pairing_codes: dict = {}
        self.current_situation = situation

    def consciousness(self) -> list:
        """Build the conscious thinking sequence as a list of callables."""
        from application.core.brain.mind import conscious
        from functools import partial

        return [
            partial(conscious.recognize, self.memory, self.persona, self.meanings, self.identity, self.say, self.express_thinking),
            partial(conscious.realize, self.memory, self.persona, self.identity, self.express_thinking),
            partial(conscious.understand, self.memory, self.persona, self.meanings, self.identity, self.escalate, self.express_thinking),
            partial(conscious.acknowledge, self.memory, self.persona, self.identity, self.say, self.express_thinking),
            partial(conscious.decide, self.memory, self.persona, self.identity, self.express_thinking),
            partial(conscious.conclude, self.memory, self.persona, self.identity, self.say, self.express_thinking),
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

    # ── Signals ──────────────────────────────────────────────────────────────

    def trigger(self, signal: Signal) -> None:
        """Accept an outside signal. Ignored when worker is stopped."""
        logger.info("Trigger signal", {"persona": self.persona, "signal": signal})
        if self.worker.stopped:
            logger.warning("Signal ignored, worker is stopped", {"persona": self.persona, "signal": signal})
            return
        from application.core.brain import situation
        self.current_situation = situation.normal
        self.memory.trigger(signal)
        self.worker.nudge()

    def incept(self, perception: Perception) -> None:
        """Inject a perception directly, bypassing understanding."""
        logger.info("Incept perception", {"persona": self.persona, "perception": perception})
        self.memory.incept(perception)
        self.worker.nudge()

    async def express_thinking(self) -> None:
        """Signal to all active channels that the persona is working on something."""
        from application.core import gateways
        from application.platform import telegram
        for channel in gateways.of(self.persona).all_channels():
            if channel.type == "telegram":
                try:
                    token = (channel.credentials or {})["token"]
                    await telegram.async_typing_action(token, channel.name)
                except Exception:
                    pass

    async def say(self, text: str) -> None:
        """Append to conversation.jsonl and send to all active channels."""
        logger.debug("Say", {"persona": self.persona, "text": text})
        from application.core import channels
        paths.append_jsonl(paths.conversation(self.persona.id), {
            "role": "persona",
            "content": text,
            "channel": "web",
            "time": datetimes.iso_8601(datetimes.now()),
        })
        await channels.send_all(self.persona, text)

    def read(self) -> list[Signal]:
        """Return all signals in the mind sorted by creation time."""
        logger.info("Read signals", {"persona": self.persona})
        return sorted(self.memory.signals, key=lambda s: s.created_at)

    # ── Learning ─────────────────────────────────────────────────────────────

    async def learn(self, conversation: str) -> None:
        """Run subconscious knowledge extraction on the given conversation text."""
        logger.debug("Learn", {"persona": self.persona})
        from application.core.brain.mind import subconscious as sub

        if not conversation.strip():
            logger.warning("No conversations to learn from", {"persona": self.persona})
            return

        await sub.person_identity(self.persona, conversation)
        await sub.person_traits(self.persona, conversation)
        await sub.wishes(self.persona, conversation)
        await sub.struggles(self.persona, conversation)
        await sub.persona_trait(self.persona, conversation)
        await sub.synthesize_dna(self.persona)

    async def learn_from_experience(self) -> None:
        """Learn from conversation, archive it, build briefing, clean completed thoughts."""
        logger.debug("Learn from experience", {"persona": self.persona})
        from application.core.brain.data import SignalEvent

        # 1. Read conversation and learn from it
        conversation = paths.read_jsonl(paths.conversation(self.persona.id))
        if not conversation:
            return

        conversation_text = "\n".join(
            f"{'Person' if entry['role'] == 'person' else 'Persona'}: {entry['content']}"
            for entry in conversation
        )

        await self.learn(conversation_text)

        # 2. Archive conversation as a single history file
        lines = []
        for entry in conversation:
            lines.append(f"[{entry.get('time', '')}] {entry['role']}: {entry['content']}")
        filename = paths.add_history_entry(self.persona.id, "conversation", "\n".join(lines))

        # 3. Build briefing from recap signals in completed thoughts
        recaps = []
        for thought in self.memory.intentions:
            for s in reversed(thought.perception.thread):
                if s.event == SignalEvent.recap:
                    recaps.append(s.content)
                    break
        recap_text = " | ".join(recaps) if recaps else "No recap available."
        date = datetimes.iso_8601(datetimes.now())
        paths.append_line(paths.history_briefing(self.persona.id),
                          f"- {date}: {filename} — {recap_text}")

        # 4. Clean all remaining thoughts
        for thought in list(self.memory.intentions):
            self.memory.forget(thought)

        # 5. Clear conversation file
        from application.platform import filesystem
        filesystem.write(paths.conversation(self.persona.id), "")

    # ── Identity ───────────────────────────────────────────────────────────

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

        return "\n\n".join(sections)

    # ── Escalation ────────────────────────────────────────────────────────

    async def escalate(self, thread_text: str, existing_meanings: list) -> str | None:
        """Generate meaning code via frontier or local model. Returns Python source or None."""
        logger.debug("ego.escalate", {"persona": self.persona, "thread": thread_text})
        from application.core.brain.mind import conscious
        from application.core.brain.mind import meanings as meanings_module

        prompt = (
            "You are generating a capability for an AI persona.\n\n"
            f"## Consciousness\n\n{conscious.document()}\n\n"
            f"## Meanings\n\n{meanings_module.document()}\n\n"
            f"## Current Meanings\n\n{meanings_module.prompt(existing_meanings)}\n\n"
            "If any existing meaning can handle the situation below, return JSON:\n"
            '{"existing": "Meaning Name"}\n\n'
            f"## Situation\n\n{thread_text}\n\n"
            f"## Available Tools\n\n{tools.document()}\n\n"
            "If no existing meaning fits, return JSON with valid Python source code:\n"
            '{"new_meaning": "python code here"}\n\n'
            "Only import: `from application.core.brain.data import Meaning`\n"
            "Do not duplicate existing meanings.\n"
            "Do not override run() unless custom logic is needed beyond tool dispatch."
        )

        code = None
        if self.persona.frontier:
            try:
                response = await models.chat(self.persona.frontier, [{"role": "user", "content": prompt}])
                code = response.strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    lines = [l for l in lines if not l.startswith("```")]
                    code = "\n".join(lines)
            except Exception as e:
                logger.warning("ego.escalate: frontier failed", {"error": str(e)})

        if not code:
            try:
                code = await models.generate(self.persona.thinking, prompt)
            except Exception as e:
                logger.warning("ego.escalate: thinking model failed", {"error": str(e)})

        return code or None
