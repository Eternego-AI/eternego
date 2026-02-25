"""Data — the cognitive system's core data types.

Stimulus   — a raw input arriving in presence
Perception — a stimulus enriched with meaning
Thought    — a perception assigned to a thread and a role

Role determines the stream:
  - non-assistant (user, system, …) → conscious stream → will → tick
  - assistant                        → sub-conscious stream → act → trait
"""

from dataclasses import dataclass, field
from datetime import datetime

from application.platform import datetimes


@dataclass
class Stimulus:
    role: str
    content: str
    thread_id: str | None = None
    created_at: datetime = field(default_factory=datetimes.now)
    understood_at: datetime | None = None


@dataclass
class Perception:
    stimulus: Stimulus
    meaning: str
    thread_id: str | None = None
    attended_at: datetime | None = None


@dataclass
class Thought:
    thread_id: str
    role: str
    content: str
    meaning: str
    created_at: datetime = field(default_factory=datetimes.now)
    picked_at: datetime | None = None
    done_at: datetime | None = None
    producer: str | None = None
