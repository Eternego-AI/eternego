"""Memory — the mind's persistent cognitive graph."""

import uuid

from datetime import datetime

from application.core.brain.data import Signal, SignalEvent, Perception, Thought, Meaning
from application.platform import datetimes, logger, persistent_memory
from application.core import paths


class Memory:
    """Per-persona cognitive graph with disk persistence.

    Holds signals, perceptions, thoughts, and their relationships.
    Starts empty; call remember() to restore from disk.
    """

    def __init__(self, persona, meanings: list[Meaning]):
        self._persona = persona
        self._meanings = meanings
        self._signals: dict[str, Signal] = {}
        self._perceptions: dict[str, Perception] = {}
        self._thoughts: list[Thought] = []
        self._signal_perceptions: dict[str, list[str]] = {}
        self._unattended_hash: int | None = None
        self._storage_id = f"mind:{persona.id}"

    # ── Persistence ──────────────────────────────────────────────────────────

    def remember(self) -> None:
        """Load graph state from disk."""
        logger.debug("memory.restore", {"persona": self._persona.id})
        path = paths.mind_state(self._persona.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        persistent_memory.load(self._storage_id, path)
        entries = persistent_memory.read(self._storage_id)
        if not entries:
            return

        state = entries[0]

        role_to_event = {"user": SignalEvent.heard, "assistant": SignalEvent.answered}
        for s in state.get("signals", []):
            event = s.get("event") or role_to_event.get(s.get("role", ""), "")
            signal = Signal(
                id=s["id"],
                event=event,
                content=s["content"],
                channel_type=s.get("channel_type", ""),
                channel_name=s.get("channel_name", ""),
                message_id=s.get("message_id", ""),
                created_at=datetime.fromisoformat(s["created_at"]),
            )
            self._signals[signal.id] = signal

        for p in state.get("perceptions", []):
            perception = Perception(impression=p["impression"])
            for sig_id in p.get("thread", []):
                if sig_id in self._signals:
                    perception.thread.append(self._signals[sig_id])
            self._perceptions[perception.impression] = perception

        self._signal_perceptions = {
            k: list(v) for k, v in state.get("signal_perceptions", {}).items()
        }

        meaning_map = {m.name: m for m in self._meanings}
        for t in state.get("thoughts", []):
            impression = t["perception"]
            meaning_name = t["meaning"]
            if impression not in self._perceptions or meaning_name not in meaning_map:
                logger.warning("memory.restore: skipping thought", {
                    "impression": impression, "meaning": meaning_name,
                })
                continue
            thought = Thought(
                perception=self._perceptions[impression],
                meaning=meaning_map[meaning_name],
                priority=t.get("priority", 0),
                id=t["id"],
            )
            self._thoughts.append(thought)

        logger.debug("memory.restore loaded", {
            "signals": len(self._signals),
            "perceptions": len(self._perceptions),
            "thoughts": len(self._thoughts),
        })

    def persist(self) -> None:
        """Save graph state to disk."""
        logger.debug("memory.persist", {"persona": self._persona.id})
        state = {
            "signals": [
                {
                    "id": s.id,
                    "event": s.event,
                    "content": s.content,
                    "channel_type": s.channel_type,
                    "channel_name": s.channel_name,
                    "message_id": s.message_id,
                    "created_at": s.created_at.isoformat(),
                }
                for s in self._signals.values()
            ],
            "perceptions": [
                {
                    "impression": p.impression,
                    "thread": [s.id for s in p.thread],
                }
                for p in self._perceptions.values()
            ],
            "thoughts": [
                {
                    "perception": t.perception.impression,
                    "meaning": t.meaning.name,
                    "priority": t.priority,
                    "id": t.id,
                }
                for t in self._thoughts
            ],
            "signal_perceptions": dict(self._signal_perceptions),
        }

        persistent_memory.clear(self._storage_id)
        persistent_memory.append(self._storage_id, state)
        logger.debug("memory.persist saved", {
            "signals": len(self._signals),
            "perceptions": len(self._perceptions),
            "thoughts": len(self._thoughts),
        })

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def persona(self):
        return self._persona

    @property
    def meanings(self) -> list:
        return list(self._meanings)

    def add_meanings(self, *new_meanings) -> None:
        """Add meanings to the live list (for runtime escalation)."""
        logger.debug("memory.add_meanings", {"persona": self._persona.id})
        self._meanings.extend(new_meanings)

    # ── Incoming ──────────────────────────────────────────────────────────────

    def trigger(self, signal: Signal) -> None:
        """Accept an outside signal into the mind."""
        logger.debug("memory.trigger", {"persona": self._persona.id, "signal": signal.id})
        self._signals[signal.id] = signal


    def incept(self, perception: Perception) -> None:
        """Inject a perception directly, bypassing understanding."""
        logger.debug("memory.incept", {"persona": self._persona.id, "impression": perception.impression})
        for signal in perception.thread:
            self._signals[signal.id] = signal
            self._signal_perceptions.setdefault(signal.id, [])
            if perception.impression not in self._signal_perceptions[signal.id]:
                self._signal_perceptions[signal.id].append(perception.impression)
        self._perceptions[perception.impression] = perception


    # ── Signal views ──────────────────────────────────────────────────────────

    @property
    def signals(self) -> list[Signal]:
        """All Signal nodes in the graph."""
        return list(self._signals.values())

    @property
    def needs_realizing(self) -> list[Signal]:
        """Heard signals not yet attached to any Perception."""
        return [s for s in self._signals.values()
                if s.event == SignalEvent.heard and s.id not in self._signal_perceptions]

    # ── Perception views ──────────────────────────────────────────────────────

    @property
    def perceptions(self) -> list[Perception]:
        """All Perceptions in the graph."""
        return list(self._perceptions.values())

    @property
    def needs_understanding(self) -> list[Perception]:
        """Perceptions not yet assigned a Meaning (no Thought exists)."""
        understood = {t.perception.impression for t in self._thoughts}
        return [p for p in self._perceptions.values()
                if p.impression not in understood]

    @property
    def most_important_perception(self) -> Perception | None:
        """The oldest perception not yet understood — first to be matched."""
        ununderstood = self.needs_understanding
        if not ununderstood:
            return None
        return min(ununderstood,
                   key=lambda p: p.thread[0].created_at if p.thread else datetimes.now())

    # ── Thought views ─────────────────────────────────────────────────────────

    def _last_event(self, thought: Thought) -> str:
        """Return the last signal's event in a thought's thread, or empty string."""
        thread = thought.perception.thread
        return thread[-1].event if thread else ""

    @property
    def intentions(self) -> list[Thought]:
        """All active Thoughts."""
        return list(self._thoughts)

    @property
    def needs_recognition(self) -> list[Thought]:
        """Thoughts that need the persona to recognize — reply or clarify."""
        result = []
        for t in self._thoughts:
            last = self._last_event(t)
            if last in (SignalEvent.heard, SignalEvent.queried, SignalEvent.nudged) and t.meaning.reply() is not None:
                result.append(t)
            elif last == SignalEvent.executed and t.meaning.clarify() is not None:
                result.append(t)
        return result

    @property
    def needs_decision(self) -> list[Thought]:
        """Thoughts ready for deciding — has path, recognition is done or not needed."""
        result = []
        for t in self._thoughts:
            if not t.meaning.path():
                continue
            last = self._last_event(t)
            if last in (SignalEvent.heard, SignalEvent.queried, SignalEvent.nudged) and t.meaning.reply() is None:
                result.append(t)
            elif last in (SignalEvent.answered, SignalEvent.clarified):
                result.append(t)
            elif last == SignalEvent.executed and t.meaning.clarify() is None:
                result.append(t)
        return result

    @property
    def needs_conclusion(self) -> list[Thought]:
        """Thoughts ready for conclusion — recap present."""
        return [t for t in self._thoughts
                if self._last_event(t) == SignalEvent.recap]

    @property
    def needs_archive(self) -> list[Thought]:
        """Thoughts done — summarized, or answered with no path."""
        result = []
        for t in self._thoughts:
            last = self._last_event(t)
            if last == SignalEvent.summarized:
                result.append(t)
            elif last == SignalEvent.answered and not t.meaning.path():
                result.append(t)
        return result

    def most_important_thought(self, thoughts: list[Thought]) -> Thought | None:
        """The highest-priority Thought — highest priority, then oldest by id."""
        if not thoughts:
            return None
        return min(thoughts, key=lambda t: (-t.priority, t.id))

    def prompts(self, thought: Thought) -> list[dict]:
        """Build role-based prompt messages for a thought, collapsing before the latest summary."""
        from application.core.brain import perceptions

        thread = thought.perception.thread
        start = 0
        for i in range(len(thread) - 1, -1, -1):
            if thread[i].event == SignalEvent.summarized:
                start = i
                break
        return perceptions.to_messages(thread[start:])

    # ── Mutation methods ──────────────────────────────────────────────────────

    def realize(self, signal: Signal, impression: str) -> None:
        """Attach signal to a perception. Only free existing thoughts when the person speaks."""
        logger.debug("memory.realize", {"persona": self._persona.id, "signal": signal.id, "impression": impression})
        if impression not in self._perceptions:
            self._perceptions[impression] = Perception(impression=impression)
        perception = self._perceptions[impression]
        perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(impression)

        if signal.event == SignalEvent.heard:
            for t in list(self._thoughts):
                if t.perception.impression == impression:
                    self._thoughts.remove(t)

    def question(self, thought: Thought) -> None:
        """Add a pre-formed thought directly (bypasses realize + understand)."""
        logger.debug("memory.question", {"persona": self._persona.id, "thought": thought.id})
        self._thoughts.append(thought)


    def understand(self, perception: Perception, meaning, priority: int = 0) -> Thought:
        """Create a Thought from a Perception and a Meaning instance."""
        logger.debug("memory.understand", {"persona": self._persona.id, "impression": perception.impression})
        thought = Thought(perception=perception, meaning=meaning, priority=priority)
        self._thoughts.append(thought)

        return thought

    def answer(self, thought: Thought, text: str, event: SignalEvent = SignalEvent.answered) -> None:
        """Append a persona signal to the thread with the given event."""
        logger.debug("memory.answer", {"persona": self._persona.id, "thought": thought.id, "event": event})
        signal = Signal(id=str(uuid.uuid4()), event=event, content=text)
        self._signals[signal.id] = signal
        thought.perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if thought.perception.impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(thought.perception.impression)


    def inform(self, thought: Thought, signal: Signal) -> None:
        """Append a signal (tool result) directly into the thread."""
        logger.debug("memory.inform", {"persona": self._persona.id, "thought": thought.id, "signal": signal.id})
        self._signals[signal.id] = signal
        thought.perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if thought.perception.impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(thought.perception.impression)


    def forget(self, thought: Thought) -> None:
        """Remove thought and its exclusive Signals from the graph."""
        logger.debug("memory.forget", {"persona": self._persona.id, "thought": thought.id})
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
        if thought in self._thoughts:
            self._thoughts.remove(thought)
        else:
            logger.warning("memory.forget: thought not found in list", {"impression": impression})

    def archive(self, thought: Thought) -> str:
        """Save a thought's conversation to history and forget it."""
        from application.core.brain import perceptions

        text = perceptions.conversation(thought.perception)
        filename = paths.add_history_entry(self._persona.id, thought.perception.impression, text)
        self.forget(thought)
        return filename


    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def settled(self) -> bool:
        """True when the mind has nothing left to process."""
        return (not self.needs_realizing
                and not self.needs_understanding
                and not self.needs_recognition
                and not self.needs_decision
                and not self.needs_conclusion)

    # ── Change detection ──────────────────────────────────────────────────────

    def changed(self) -> bool:
        """True when unattended signals have changed since last check."""
        unattended = self.needs_realizing
        if not unattended:
            self._unattended_hash = None
            return False
        current = hash(frozenset(s.id for s in unattended))
        if current != self._unattended_hash:
            self._unattended_hash = current
            return True
        return False
