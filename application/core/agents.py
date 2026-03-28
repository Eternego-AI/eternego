"""Agents — persona lifecycle management and runtime state."""

import secrets

from datetime import timedelta

from application.core.brain.data import Signal, Perception, Thought
from application.core.brain.mind.memory import Memory
from application.core.brain import character
from application.core import local_model, frontier, tools, paths
from application.core.data import Persona, Channel
from application.core.exceptions import MindError, AgentError
from application.platform import datetimes, logger

_personas: dict[str, "Ego"] = {}


def register(p: Persona, ego: "Ego") -> None:
    """Store a constructed ego and start the tick."""
    logger.info("Registering agent", {"persona": p})
    _personas[p.id] = ego
    from application.core.brain.mind import clock
    ego.worker.run(clock.tick, ego.memory, ego.worker)


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
        self.memory = Memory(p, all_meanings)
        self.memory.remember()
        self.pairing_codes: dict = {}
        self.current_situation = situation

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

    def question(self, thought: Thought) -> None:
        """Inject a pre-formed thought, bypassing understanding and recognition."""
        logger.info("Question", {"persona": self.persona, "thought": thought})
        self.memory.incept(thought.perception)
        self.memory.question(thought)
        self.worker.nudge()

    def read(self) -> list[Signal]:
        """Return all signals in the mind sorted by creation time."""
        logger.info("Read signals", {"persona": self.persona})
        return sorted(self.memory.signals, key=lambda s: s.created_at)

    # ── Learning ─────────────────────────────────────────────────────────────

    async def learn(self, messages: list[dict]) -> None:
        """Run subconscious knowledge extraction on the given conversation messages."""
        logger.info("Learn", {"persona": self.persona})
        from application.core.brain.mind import subconscious as sub

        if not messages:
            logger.warning("No conversations to learn from", {"persona": self.persona})
            return

        await sub.person_identity(self.persona, messages)
        await sub.person_traits(self.persona, messages)
        await sub.wishes(self.persona, messages)
        await sub.struggles(self.persona, messages)
        await sub.persona_context(self.persona, messages)
        await sub.synthesize_dna(self.persona)

    async def learn_from_experience(self) -> None:
        """Learn from all thoughts, then archive each individually."""
        logger.info("Learn from experience", {"persona": self.persona})
        from application.core.brain import perceptions

        mem = self.memory

        all_thoughts = list(mem.intentions)
        if not all_thoughts:
            return

        messages = []
        for thought in all_thoughts:
            messages.extend(perceptions.to_conversation(thought.perception.thread))

        await self.learn(messages)

        for thought in all_thoughts:
            from application.core.brain.data import SignalEvent
            summaries = [s for s in thought.perception.thread if s.event == SignalEvent.summarized]
            recap = summaries[-1].content if summaries else None

            filename = mem.archive(thought)

            if recap:
                paths.add_history_briefing(self.persona.id, "| File | Recap |", f"| {filename} | {recap} |")

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

        available_tools = tools.discover()
        existing = [{"name": m.name, "description": m.description()}
                    for m in existing_meanings if m.name != "Escalation"]

        tools_text = "\n".join(
            f"- `{t.name}({', '.join(f'{k}: {v}' for k, v in t.params.items())}) -> {t.returns}`: {t.instruction}"
            for t in available_tools
        ) or "(no tools available)"

        meanings_text = "\n".join(
            f"- {m['name']}: {m['description']}" for m in existing
        ) or "(none yet)"

        prompt = (
            "# Meaning Generation\n\n"
            "A persona has a cognitive pipeline that processes interactions in five stages:\n"
            "  realize → understand → recognize → decide → conclude\n\n"
            "A **Meaning** is a Python class that defines how the persona handles a specific "
            "type of interaction. When no existing Meaning matches, a new one must be created.\n\n"
            "## How Meanings Work in the Pipeline\n\n"
            "Each Meaning method maps to a pipeline stage. A small local model executes "
            "these — prompts must be explicit, unambiguous, and structured.\n\n"
            "### `name` (class attribute)\n"
            "A specific, descriptive identifier. This appears in the recognition list alongside "
            "existing meanings, so it must be **narrower and more specific** than built-in names. "
            "The local model picks meanings by name + description, so specificity avoids collisions.\n"
            "Good: 'Weather Forecast Lookup', 'Email Draft Composition'\n"
            "Bad: 'Helper', 'Task', 'Utility'\n\n"
            "### `description() → str`\n"
            "One sentence defining exactly what interactions this meaning covers. Used by the "
            "understand stage to match a conversation to this meaning. Must be distinct from "
            "every existing meaning — if it overlaps, the local model will pick the wrong one.\n\n"
            "### `reply() → str | None`\n"
            "Prompt for the **recognize** stage — how to respond to the person on first contact. "
            "This runs BEFORE any action is taken.\n"
            "CRITICAL: The reply output is appended to the conversation thread and becomes "
            "visible to the decide stage. Never ask the model to state specific extracted values "
            "(times, dates, names, quantities) in the reply — if it gets them wrong, the error "
            "propagates into the extraction. Keep it to a brief acknowledgment.\n"
            "Return None if no verbal response is needed before acting.\n\n"
            "### `clarify() → str | None`\n"
            "Prompt for retry after an error. Only runs when an action has failed and the "
            "conversation already contains an error message. Tell the model to look at the error, "
            "explain what went wrong, and ask the person to confirm or correct.\n"
            "Return None if retries should be silent.\n\n"
            "### `path() → str | None`\n"
            "Prompt for the **decide** stage — tells the local model what structured data to extract "
            "or what action to take. The model sees the full conversation thread and must return JSON.\n"
            "CRITICAL: Tell the model to extract information from what the **person** said, "
            "not from assistant messages in the thread.\n"
            "For tool-using meanings, reference tools by their exact name and define the exact "
            "JSON schema the model must return.\n"
            "Return None for conversational-only meanings (no action needed).\n\n"
            "### `summarize() → str | None`\n"
            "Prompt for the **conclude** stage — the final message to the person after the action "
            "completes. Should confirm what was done. Return None to skip.\n\n"
            "### `run(persona_response: dict)` — do NOT implement unless needed\n"
            "The default `run()` dispatches tool calls from the JSON that `path()` produced. "
            "Do not override it unless the meaning needs custom logic (like file I/O).\n"
            "`run()` returns an async callable or None. The callable is executed by the pipeline, "
            "which handles all errors. The callable returns a string (execution output fed back "
            "to the conversation) or None (success, nothing to report).\n"
            "Raise exceptions for validation failures — do not catch them.\n"
            "Example override:\n"
            "    async def run(self, persona_response: dict):\n"
            "        value = persona_response.get('key', '')\n"
            "        if not value:\n"
            "            raise ValueError('key is missing')\n"
            "        async def action():\n"
            "            return do_something(value)\n"
            "        return action\n\n"
            f"## Conversation That Triggered Escalation\n\n{thread_text}\n\n"
            f"## Available Tools\n\n{tools_text}\n\n"
            f"## Existing Meanings (do not duplicate or overlap)\n\n{meanings_text}\n\n"
            "## Output\n\n"
            "Return ONLY valid Python source code. No markdown fences, no explanation.\n"
            "Only import: `from application.core.brain.data import Meaning`\n\n"
            "from application.core.brain.data import Meaning\n\n\n"
            "class SpecificDescriptiveName(Meaning):\n"
            '    name = "Specific Descriptive Name"\n\n'
            "    def description(self):\n"
            '        return "Narrow, specific description of what this covers."\n\n'
            "    def clarify(self):\n"
            '        return "Look at the error. Explain what went wrong and ask the person to correct."\n\n'
            "    def reply(self):\n"
            '        return "Acknowledge briefly. Do not restate extracted details."\n\n'
            "    def summarize(self):\n"
            '        return "Confirm what was done."\n\n'
            "    def path(self):\n"
            "        return (\n"
            '            "Extract X from what the person said (ignore assistant messages).\\n"\n'
            "            'Return JSON: {\"tool\": \"name\", \"param\": \"value\"}\\n'\n"
            "        )\n"
        )

        code = None
        if self.persona.frontier:
            try:
                response = await frontier.chat(self.persona.frontier, prompt)
                code = response.strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    lines = [l for l in lines if not l.startswith("```")]
                    code = "\n".join(lines)
            except Exception as e:
                logger.warning("ego.escalate: frontier failed", {"error": str(e)})

        if not code:
            try:
                code = await local_model.generate(self.persona.model.name, prompt)
            except Exception as e:
                logger.warning("ego.escalate: local model failed", {"error": str(e)})

        return code or None
