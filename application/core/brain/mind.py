"""Mind — the persona's cognitive memory and shared interface for all thinking modules."""

import asyncio

from application.core.brain.data import Signal, Perception, Thought
from application.platform import datetimes, logger


class Mind:

    def __init__(self, persona):
        self._persona = persona
        self._signals: dict[str, Signal] = {}
        self._perceptions: dict[str, Perception] = {}      # keyed by impression
        self._thoughts: list[Thought] = []
        self._signal_perceptions: dict[str, list[str]] = {} # signal.id → [impression, ...]
        self._signal_hash: int | None = None               # None forces first changed() → True
        self._tick_task: asyncio.Task | None = None

    @classmethod
    def load(cls, persona) -> "Mind":
        """Create a Mind for this persona, register it, and start thinking."""
        from application.core import registry
        m = cls(persona)
        registry.save(persona, m)
        m.start_thinking()
        return m

    def start_thinking(self) -> None:
        """Start the cognitive tick loop."""
        if self._tick_task is None or self._tick_task.done():
            from application.core.brain import clock
            self._tick_task = asyncio.create_task(clock.tick(self))

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def persona(self):
        return self._persona

    # ── Incoming ──────────────────────────────────────────────────────────────

    async def receive(self, signal: Signal) -> None:
        logger.info("mind.receive", {"id": signal.id, "role": signal.role})
        self._signals[signal.id] = signal

    # ── Signal views ──────────────────────────────────────────────────────────

    @property
    def signals(self) -> list[Signal]:
        """All Signal nodes in the graph."""
        return list(self._signals.values())

    @property
    def unrealized(self) -> list[Signal]:
        """User-role Signals not yet attached to any Perception."""
        return [s for s in self._signals.values()
                if s.role == "user" and s.id not in self._signal_perceptions]

    @property
    def realization(self) -> list[Signal]:
        """Signals already attached to at least one Perception."""
        return [s for s in self._signals.values()
                if s.id in self._signal_perceptions]

    # ── Perception views ──────────────────────────────────────────────────────

    @property
    def perceptions(self) -> list[Perception]:
        """All Perceptions in the graph."""
        return list(self._perceptions.values())

    @property
    def awareness(self) -> list[Perception]:
        """Perceptions whose Thought is still in progress."""
        open_impressions = {t.perception.impression for t in self._thoughts
                            if t.processed_at is None}
        return [p for p in self._perceptions.values()
                if p.impression in open_impressions]

    @property
    def unrecognized(self) -> list[Perception]:
        """Perceptions not yet assigned a Meaning (no Thought exists)."""
        recognized = {t.perception.impression for t in self._thoughts}
        return [p for p in self._perceptions.values()
                if p.impression not in recognized]

    @property
    def most_important_perception(self) -> Perception | None:
        """The oldest unrecognized Perception — first to be recognized."""
        unrecognized = self.unrecognized
        if not unrecognized:
            return None
        return min(unrecognized,
                   key=lambda p: p.thread[0].created_at if p.thread else datetimes.now())

    # ── Thought views ─────────────────────────────────────────────────────────

    @property
    def intentions(self) -> list[Thought]:
        """All active Thoughts."""
        return list(self._thoughts)

    @property
    def unanswered(self) -> list[Thought]:
        """Thoughts where the latest thread Signal has role=user."""
        result = []
        for t in self._thoughts:
            if t.processed_at is not None:
                continue
            thread = t.perception.thread
            if thread and thread[-1].role == "user":
                result.append(t)
        return result

    @property
    def pending(self) -> list[Thought]:
        """Thoughts with processed_at=None whose meaning has a path."""
        return [t for t in self._thoughts
                if t.processed_at is None and t.meaning.path()]

    @property
    def concluded(self) -> list[Thought]:
        """Thoughts with processed_at set, ready for concluding."""
        return [t for t in self._thoughts if t.processed_at is not None]

    def most_important_thought(self, thoughts: list[Thought]) -> Thought | None:
        """The highest-priority Thought — lowest order, then oldest by id."""
        if not thoughts:
            return None
        return min(thoughts, key=lambda t: (t.order, t.id))

    # ── Context ───────────────────────────────────────────────────────────────

    @property
    def context(self) -> list[Signal]:
        """All system-role Signals (persistent context from recaps)."""
        return [s for s in self._signals.values() if s.role == "system"]

    # ── Mutation methods ──────────────────────────────────────────────────────

    def understand(self, signal: Signal, impression: str) -> None:
        """Attach signal to the Perception with this impression; create if new."""
        if impression not in self._perceptions:
            self._perceptions[impression] = Perception(impression=impression)
        perception = self._perceptions[impression]
        if signal not in perception.thread:
            perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(impression)

    def recognize(self, perception: Perception, meaning, order: int = 0) -> Thought:
        """Create a Thought from a Perception and a Meaning instance."""
        thought = Thought(perception=perception, meaning=meaning, order=order)
        self._thoughts.append(thought)
        logger.info("mind.recognize", {"impression": perception.impression,
                                       "meaning": type(meaning).__name__,
                                       "order": order})
        return thought

    def answer(self, thought: Thought, text: str) -> None:
        """Append an assistant Signal to the thread."""
        signal = Signal(role="assistant", content=text)
        self._signals[signal.id] = signal
        thought.perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if thought.perception.impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(thought.perception.impression)

    def resolve(self, thought: Thought) -> None:
        """Mark thought as processed (sets processed_at)."""
        thought.processed_at = datetimes.now()
        logger.info("mind.resolve", {"thought_id": thought.id})

    def inform(self, thought: Thought, signal: Signal) -> None:
        """Append a user Signal (tool result) directly into the thread."""
        self._signals[signal.id] = signal
        thought.perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if thought.perception.impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(thought.perception.impression)

    def remember(self, text: str) -> None:
        """Create a system Signal and add it to context."""
        signal = Signal(role="system", content=text)
        self._signals[signal.id] = signal
        logger.info("mind.remember", {"length": len(text)})

    def forget(self, thought: Thought) -> None:
        """Remove thought and its exclusive Signals from the graph."""
        impression = thought.perception.impression
        other_impressions = {t.perception.impression for t in self._thoughts
                             if t is not thought}
        for signal in list(thought.perception.thread):
            related = set(self._signal_perceptions.get(signal.id, []))
            shared = related & other_impressions
            if not shared:
                self._signals.pop(signal.id, None)
                self._signal_perceptions.pop(signal.id, None)
            else:
                self._signal_perceptions[signal.id] = [
                    p for p in self._signal_perceptions[signal.id] if p != impression
                ]
        self._perceptions.pop(impression, None)
        self._thoughts.remove(thought)
        logger.info("mind.forget", {"impression": impression})

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def stop_thinking(self) -> None:
        """Cancel the running tick task."""
        if self._tick_task and not self._tick_task.done():
            self._tick_task.cancel()
        self._tick_task = None

    def snapshot(self) -> list[tuple[str, list]]:
        """Return all active perceptions as (impression, thread) pairs for archiving."""
        return [(p.impression, list(p.thread)) for p in self._perceptions.values()]

    def clear(self) -> None:
        """Wipe all in-memory state."""
        self._signals.clear()
        self._perceptions.clear()
        self._thoughts.clear()
        self._signal_perceptions.clear()
        self._signal_hash = hash(frozenset())  # match empty state; next changed() → False

    # ── Change detection ──────────────────────────────────────────────────────

    def changed(self) -> bool:
        """True when user-role signals have changed since last call."""
        current = hash(frozenset(s.id for s in self._signals.values() if s.role == "user"))
        if current != self._signal_hash:
            self._signal_hash = current
            return True
        return False
