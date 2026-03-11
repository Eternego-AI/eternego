"""Brain data models — Signal, Perception, Thought."""

import time
from dataclasses import dataclass, field
from datetime import datetime

from application.platform import datetimes


@dataclass
class Signal:
    """Atomic unit of communication. Every message becomes a Signal node in the mind graph."""
    role: str               # user | assistant | system
    content: str
    channel_type: str = ""
    channel_name: str = ""
    message_id: str = ""
    created_at: datetime = field(default_factory=datetimes.now)
    id: str = field(default="")

    def __post_init__(self):
        if not self.id:
            if self.channel_type and self.channel_name and self.message_id:
                self.id = f"{self.channel_type}-{self.channel_name}-{self.message_id}"
            else:
                self.id = str(time.time_ns())


@dataclass
class Perception:
    """A group of related Signals forming a thread. Impression is the unique key."""
    impression: str                             # unique label; e.g. "Ask for reminder at 10am"
    thread: list[Signal] = field(default_factory=list)


@dataclass
class Thought:
    """A Perception with a matched Meaning — the cognitive work unit."""
    perception: Perception
    meaning: object         # Meaning instance
    order: int = 0          # importance rank from recognization; lower = more important
    id: str = field(default_factory=lambda: str(time.time_ns()))
    processed_at: datetime | None = None
