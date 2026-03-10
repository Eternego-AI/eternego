"""Mind — the persona's cognitive state.

One Mind instance per persona, loaded once at startup.

Public interface:
  receive(prompt, verbosity)  add a signal and start the tick loop.
  reply(text)                 send text to the person via the latest channel.
  archive(perception, recap)  save conversation to history, clean memory, emit archive_done.
  clear()                     clear all memory.

Internal structure:
  Memory — the cognitive graph (nodes + edges)
  Tick   — the module loop (conclusion → authorize → realize → ... → identity modules)
"""

from application.core.brain.mind.memory import Memory
from application.core.brain.mind.tick import Tick
from application.core.brain.data import Signal, Perception
from application.core.data import Persona, Prompt
from application.platform import logger, datetimes


class Mind:

    def __init__(self, persona_id: str):
        self._persona_id = persona_id
        self.memory = Memory(persona_id)
        self.memory.load()
        self._tick: Tick | None = None  # created lazily after persona is available

    @classmethod
    def load(cls, persona: Persona) -> "Mind":
        """Create and register a Mind for this persona."""
        m = cls(persona.id)
        from application.core import registry
        registry.save(persona, m)
        logger.info("mind.load", {
            "persona_id": persona.id,
            "nodes": len(m.memory.nodes),
        })
        return m

    @property
    def _persona(self) -> Persona | None:
        from application.core import registry
        return registry.get_persona(self._persona_id)

    def _ensure_tick(self) -> Tick:
        if self._tick is None:
            persona = self._persona
            if persona is None:
                raise RuntimeError(f"mind: persona not found for {self._persona_id}")
            self._tick = Tick(self._persona_id, self.memory, persona)
        return self._tick

    def receive(self, prompt: Prompt, verbosity: str = "conversational") -> None:
        """Add a user signal to memory and start the tick loop."""
        logger.info("mind.receive", {"persona_id": self._persona_id, "verbosity": verbosity, "content": prompt.content[:60]})

        signal = Signal(role="user", data={"content": prompt.content, "verbosity": verbosity})
        self.memory.add_node(signal)
        self.memory.persist()
        self._ensure_tick().start()

    async def reply(self, text: str) -> None:
        """Send text to the person via the latest channel."""
        logger.info("mind.reply", {"persona_id": self._persona_id, "text": text[:80]})

        from application.core import channels
        persona = self._persona
        if persona is None:
            return
        channel = channels.latest(persona) or channels.default_channel(persona)
        if channel:
            await channels.send(channel, text)


    async def archive(self, perception: Perception, recap: str | None = None) -> None:
        """Save conversation to history, clean memory, produce archive_done signal."""
        logger.debug("Archiving a conversation", {"persona_id": self._persona_id, "perception_id": perception.id, "text": recap[:80]})

        from application.core import paths
        from application.platform import datetimes as dt_module

        # Format history from user/assistant/result signals
        lines = []
        for s in perception.signals:
            time = s.created_at.strftime("%Y-%m-%d %H:%M UTC")
            if s.role == "user":
                lines.append(f"[at {time}] person: {s.data.get('content', '')}")
            elif s.role == "assistant":
                lines.append(f"[at {time}] {s.data.get('content', '')}")
            elif s.role == "result":
                lines.append(f"[at {time}] [{s.data.get('tool', '?')}]: {s.data.get('output', '')}")

        label = (recap or perception.impression or "conversation")[:50].replace("/", "-").replace("\\", "-")
        paths.add_history_entry(self._persona_id, label, "\n".join(lines))

        if recap:
            timestamp = dt_module.date_stamp(dt_module.now())
            paths.add_history_briefing(
                self._persona_id,
                "| Date | Recap | File |",
                f"| {timestamp} | {recap} | {label}-{timestamp}.md |",
            )
            filename = f"{label}-{timestamp}.md"
        else:
            filename = f"{label}.md"

        # Remove all signals with perceived_as edge to this perception
        signal_ids = [
            e.src_id for e in self.memory.edges
            if e.dst_id == perception.id and e.type == "perceived_as"
        ]
        for sid in signal_ids:
            self.memory.remove_node(sid)

        self.memory.remove_node(perception.id)

        # Produce archive_done information signal for identity modules
        archive_done = Signal(
            role="information",
            data={"type": "archive_done", "filename": filename},
        )
        self.memory.add_node(archive_done)

    def stop_tick(self) -> None:
        """Cancel the running tick task, if any."""
        if self._tick is not None:
            self._tick.cancel()

    def clear(self) -> None:
        """Clear all memory."""
        self.memory.clear()
        logger.info("mind.clear", {"persona_id": self._persona_id})
