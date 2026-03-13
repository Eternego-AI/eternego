"""Memory — the mind's persistent cognitive graph."""

import asyncio
import uuid

from datetime import datetime

from application.core.brain.data import Signal, Perception, Thought, Meaning
from application.platform import datetimes, logger, persistent_memory
from application.core import paths


class Memory:
    """Per-persona cognitive graph with disk persistence.

    Holds signals, perceptions, thoughts, and their relationships.
    Restores from disk on creation; caller is responsible for calling persist().
    """

    def __init__(self, persona, meanings: list[Meaning]):
        self._persona = persona
        self._meanings = meanings
        self._signals: dict[str, Signal] = {}
        self._perceptions: dict[str, Perception] = {}
        self._thoughts: list[Thought] = []
        self._signal_perceptions: dict[str, list[str]] = {}
        self._unattended_hash: int | None = None
        self._tick_task: asyncio.Task | None = None
        self._storage_id = f"mind:{persona.id}"
        self._restore()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _restore(self) -> None:
        """Load graph state from disk."""
        logger.info("memory.restore", {"persona": self._persona.id})
        path = paths.mind_state(self._persona.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        persistent_memory.load(self._storage_id, path)
        entries = persistent_memory.read(self._storage_id)
        if not entries:
            return

        state = entries[0]

        for s in state.get("signals", []):
            signal = Signal(
                id=s["id"],
                role=s["role"],
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
                processed_at=datetime.fromisoformat(t["processed_at"]) if t.get("processed_at") else None,
                concluded_at=datetime.fromisoformat(t["concluded_at"]) if t.get("concluded_at") else None,
            )
            self._thoughts.append(thought)

        logger.debug("memory.restore loaded", {
            "signals": len(self._signals),
            "perceptions": len(self._perceptions),
            "thoughts": len(self._thoughts),
        })

    def persist(self) -> None:
        """Save graph state to disk."""
        logger.info("memory.persist", {"persona": self._persona.id})
        state = {
            "signals": [
                {
                    "id": s.id,
                    "role": s.role,
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
                    "processed_at": t.processed_at.isoformat() if t.processed_at else None,
                    "concluded_at": t.concluded_at.isoformat() if t.concluded_at else None,
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
        logger.info("memory.add_meanings", {"persona": self._persona.id})
        self._meanings.extend(new_meanings)

    # ── Incoming ──────────────────────────────────────────────────────────────

    def trigger(self, signal: Signal) -> None:
        """Accept an outside signal into the mind."""
        logger.info("memory.trigger", {"persona": self._persona.id, "signal": signal.id})
        self._signals[signal.id] = signal


    def incept(self, perception: Perception) -> None:
        """Inject a perception directly, bypassing understanding."""
        logger.info("memory.incept", {"persona": self._persona.id, "impression": perception.impression})
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
    def unattended(self) -> list[Signal]:
        """User-role Signals not yet attached to any Perception."""
        return [s for s in self._signals.values()
                if s.role == "user" and s.id not in self._signal_perceptions]

    @property
    def attended(self) -> list[Signal]:
        """Signals already attached to at least one Perception."""
        return [s for s in self._signals.values()
                if s.id in self._signal_perceptions]

    # ── Perception views ──────────────────────────────────────────────────────

    @property
    def perceptions(self) -> list[Perception]:
        """All Perceptions in the graph."""
        return list(self._perceptions.values())

    @property
    def active(self) -> list[Perception]:
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
        """Thoughts ready for deciding: has path, not processed, and wondering is done.

        For meanings with no reply, deciding owns the full lifecycle.
        For meanings with a reply, deciding waits until wondering has replied
        (last signal is assistant) and the user hasn't added more signals.
        """
        result = []
        for t in self._thoughts:
            if t.processed_at is not None or not t.meaning.path():
                continue
            if t.meaning.reply() is None:
                result.append(t)
            elif t.perception.thread and t.perception.thread[-1].role == "assistant":
                result.append(t)
        return result

    @property
    def concluded(self) -> list[Thought]:
        """Thoughts with processed_at set but not yet concluded."""
        return [t for t in self._thoughts
                if t.processed_at is not None and t.concluded_at is None]

    def most_important_thought(self, thoughts: list[Thought]) -> Thought | None:
        """The highest-priority Thought — highest priority, then oldest by id."""
        if not thoughts:
            return None
        return min(thoughts, key=lambda t: (-t.priority, t.id))

    # ── Context ───────────────────────────────────────────────────────────────

    @property
    def context(self) -> list[Signal]:
        """All system-role Signals (persistent context from recaps)."""
        return [s for s in self._signals.values() if s.role == "system"]

    # ── Mutation methods ──────────────────────────────────────────────────────

    def understand(self, signal: Signal, impression: str) -> None:
        """Attach signal to the Perception with this impression; create if new."""
        logger.info("memory.understand", {"persona": self._persona.id, "signal": signal.id, "impression": impression})
        if impression not in self._perceptions:
            self._perceptions[impression] = Perception(impression=impression)
        perception = self._perceptions[impression]
        if signal not in perception.thread:
            perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(impression)


        # Free concluded thoughts so perception can be re-recognized
        for t in list(self._thoughts):
            if t.perception.impression == impression and t.concluded_at is not None:
                self._thoughts.remove(t)
                logger.debug("memory.understand: freed concluded thought", {"impression": impression})

    def question(self, thought: Thought) -> None:
        """Add a pre-formed thought directly (bypasses understand + recognize)."""
        logger.info("memory.question", {"persona": self._persona.id, "thought": thought.id})
        self._thoughts.append(thought)


    def recognize(self, perception: Perception, meaning, priority: int = 0) -> Thought:
        """Create a Thought from a Perception and a Meaning instance."""
        logger.info("memory.recognize", {"persona": self._persona.id, "impression": perception.impression})
        thought = Thought(perception=perception, meaning=meaning, priority=priority)
        self._thoughts.append(thought)

        return thought

    def answer(self, thought: Thought, text: str) -> None:
        """Append an assistant Signal to the thread."""
        logger.info("memory.answer", {"persona": self._persona.id, "thought": thought.id})
        signal = Signal(id=str(uuid.uuid4()), role="assistant", content=text)
        self._signals[signal.id] = signal
        thought.perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if thought.perception.impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(thought.perception.impression)


    def resolve(self, thought: Thought) -> None:
        """Mark thought as processed (sets processed_at)."""
        logger.info("memory.resolve", {"persona": self._persona.id, "thought": thought.id})
        thought.processed_at = datetimes.now()


    def inform(self, thought: Thought, signal: Signal) -> None:
        """Append a user Signal (tool result) directly into the thread."""
        logger.info("memory.inform", {"persona": self._persona.id, "thought": thought.id, "signal": signal.id})
        self._signals[signal.id] = signal
        thought.perception.thread.append(signal)
        self._signal_perceptions.setdefault(signal.id, [])
        if thought.perception.impression not in self._signal_perceptions[signal.id]:
            self._signal_perceptions[signal.id].append(thought.perception.impression)


    def remember(self, text: str) -> None:
        """Create a system Signal and add it to context."""
        logger.info("memory.remember", {"persona": self._persona.id})
        signal = Signal(id=str(uuid.uuid4()), role="system", content=text)
        self._signals[signal.id] = signal


    def forget(self, thought: Thought) -> None:
        """Remove thought and its exclusive Signals from the graph."""
        logger.info("memory.forget", {"persona": self._persona.id, "thought": thought.id})
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


    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def settled(self) -> bool:
        """True when the mind has nothing left to process."""
        return (not self.unattended
                and not self.unrecognized
                and not self.unanswered
                and not self.pending
                and not self.concluded)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_thinking(self) -> None:
        """Start the cognitive tick loop."""
        logger.info("memory.start_thinking", {"persona": self._persona.id})
        if self._tick_task is None or self._tick_task.done():
            from application.core.brain.mind import clock
            self._tick_task = asyncio.create_task(clock.tick(self))

    def stop_thinking(self) -> None:
        """Cancel the running tick task and persist state."""
        logger.info("memory.stop_thinking", {"persona": self._persona.id})
        if self._tick_task and not self._tick_task.done():
            self._tick_task.cancel()
        self._tick_task = None
        self.persist()

    def snapshot(self) -> list[tuple[str, list]]:
        """Return all active perceptions as (impression, thread) pairs for archiving."""
        logger.info("memory.snapshot", {"persona": self._persona.id})
        return [(p.impression, list(p.thread)) for p in self._perceptions.values()]

    def clear(self) -> None:
        """Wipe all in-memory state and persist the empty graph."""
        logger.info("memory.clear", {"persona": self._persona.id})
        self._signals.clear()
        self._perceptions.clear()
        self._thoughts.clear()
        self._signal_perceptions.clear()
        self._unattended_hash = None

        self.persist()

    # ── Change detection ──────────────────────────────────────────────────────

    def changed(self) -> bool:
        """True when unattended signals have changed since last check."""
        unattended = self.unattended
        if not unattended:
            self._unattended_hash = None
            return False
        current = hash(frozenset(s.id for s in unattended))
        if current != self._unattended_hash:
            self._unattended_hash = current
            return True
        return False
