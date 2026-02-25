"""Memory — the persona's in-process cognitive memory.

One Memory instance per persona, created at startup via load().
Never instantiate directly — load() is the only entry point.

Three in-process layers:
  presence   — raw stimuli arriving in the persona's field
  awareness  — perceptions produced by understanding
  mind       — all thoughts across the cognitive cycle

Each layer exposes asyncio.Event(s) that fire when new items arrive,
allowing clock loops to react rather than poll.

Persisted as a single file. Written after each successful stream cycle.
"""

import asyncio
import json
from datetime import datetime

from application.core.data import Persona
from application.core.brain.cognitive.data import Stimulus, Perception, Thought
from application.core import paths


class Presence:
    def __init__(self, items: list[Stimulus]):
        self.items = items
        self.changed = asyncio.Event()
        if any(s.understood_at is None for s in items):
            self.changed.set()

    def consider(self, stimulus: Stimulus) -> None:
        """Add a stimulus to presence."""
        self.items.append(stimulus)
        self.changed.set()

    def be(self) -> list[Stimulus]:
        """Return all stimuli not yet understood."""
        return [s for s in self.items if s.understood_at is None]


class Awareness:
    def __init__(self, items: list[Perception]):
        self.items = items
        self.changed = asyncio.Event()
        if any(p.attended_at is None for p in items):
            self.changed.set()

    def pay(self, perception: Perception) -> None:
        """Add a perception to awareness."""
        self.items.append(perception)
        self.changed.set()

    def be(self) -> list[Perception]:
        """Return all perceptions not yet attended to."""
        return [p for p in self.items if p.attended_at is None]

    def forget(self, perception: Perception) -> None:
        """Remove a perception — called by traits only."""
        key = perception.stimulus.created_at.isoformat()
        self.items = [p for p in self.items if p.stimulus.created_at.isoformat() != key]


class Mind:
    def __init__(self, items: list[Thought]):
        self.items = items
        self.conscious_changed = asyncio.Event()
        self.sub_conscious_changed = asyncio.Event()
        if any(t.role != "assistant" and t.picked_at is None for t in items):
            self.conscious_changed.set()
        if any(t.role == "assistant" and t.picked_at is None for t in items):
            self.sub_conscious_changed.set()

    def keep(self, thought: Thought) -> None:
        """Add a thought to mind and signal the appropriate stream."""
        self.items.append(thought)
        if thought.role == "assistant":
            self.sub_conscious_changed.set()
        else:
            self.conscious_changed.set()

    def read(self) -> list[Thought]:
        """Return all thoughts."""
        return list(self.items)


class Memory:
    def __init__(self, presence: Presence, awareness: Awareness, mind: Mind):
        self.presence = presence
        self.awareness = awareness
        self.mind = mind


async def load(persona: Persona) -> Memory:
    """Load or initialise memory for this persona. The only way to get a Memory."""
    path = paths.memory_state(persona.id)

    def parse_stimulus(d: dict) -> Stimulus:
        return Stimulus(
            role=d["role"],
            content=d["content"],
            thread_id=d.get("thread_id"),
            created_at=datetime.fromisoformat(d["created_at"]),
            understood_at=datetime.fromisoformat(d["understood_at"]) if d.get("understood_at") else None,
        )

    def parse_perception(d: dict) -> Perception:
        return Perception(
            stimulus=parse_stimulus(d["stimulus"]),
            meaning=d["meaning"],
            thread_id=d.get("thread_id"),
            attended_at=datetime.fromisoformat(d["attended_at"]) if d.get("attended_at") else None,
        )

    def parse_thought(d: dict) -> Thought:
        return Thought(
            thread_id=d["thread_id"],
            role=d["role"],
            content=d["content"],
            meaning=d["meaning"],
            created_at=datetime.fromisoformat(d["created_at"]),
            picked_at=datetime.fromisoformat(d["picked_at"]) if d.get("picked_at") else None,
            done_at=datetime.fromisoformat(d["done_at"]) if d.get("done_at") else None,
            producer=d.get("producer"),
        )

    if path.exists():
        raw = json.loads(path.read_text())
        stimuli = [parse_stimulus(d) for d in raw.get("presence", [])]
        perceptions = [parse_perception(d) for d in raw.get("awareness", [])]
        thoughts = [parse_thought(d) for d in raw.get("mind", [])]
    else:
        stimuli, perceptions, thoughts = [], [], []

    return Memory(
        presence=Presence(stimuli),
        awareness=Awareness(perceptions),
        mind=Mind(thoughts),
    )


async def save(mem: Memory, persona: Persona) -> None:
    """Persist the current memory state to disk."""
    path = paths.memory_state(persona.id)
    path.parent.mkdir(parents=True, exist_ok=True)

    def dump_stimulus(s: Stimulus) -> dict:
        return {
            "role": s.role,
            "content": s.content,
            "thread_id": s.thread_id,
            "created_at": s.created_at.isoformat(),
            "understood_at": s.understood_at.isoformat() if s.understood_at else None,
        }

    def dump_perception(p: Perception) -> dict:
        return {
            "stimulus": dump_stimulus(p.stimulus),
            "meaning": p.meaning,
            "thread_id": p.thread_id,
            "attended_at": p.attended_at.isoformat() if p.attended_at else None,
        }

    def dump_thought(t: Thought) -> dict:
        return {
            "thread_id": t.thread_id,
            "role": t.role,
            "content": t.content,
            "meaning": t.meaning,
            "created_at": t.created_at.isoformat(),
            "picked_at": t.picked_at.isoformat() if t.picked_at else None,
            "done_at": t.done_at.isoformat() if t.done_at else None,
            "producer": t.producer,
        }

    data = {
        "presence": [dump_stimulus(s) for s in mem.presence.items],
        "awareness": [dump_perception(p) for p in mem.awareness.items],
        "mind": [dump_thought(t) for t in mem.mind.items],
    }
    path.write_text(json.dumps(data, indent=2))
