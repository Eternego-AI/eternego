"""Data — the brain's core data types.

Signal    — a raw input arriving in presence (role + content + channel + timestamp)
Thread    — a group of related signals
Meaning   — a perception's title and selected tools
Perception — a thread paired with its meaning
Step      — a single tool invocation with parameters
Tool      — base class for persona capabilities
Skill     — base class for persona knowledge documents
"""

from dataclasses import dataclass, field
from datetime import datetime

from application.core.data import Prompt, Channel
from application.platform import datetimes


@dataclass
class Signal:
    prompt: Prompt
    channel: Channel | None = None
    created_at: datetime = field(default_factory=datetimes.now)
    pending_permission: list[str] = field(default_factory=list)  # blocked tool names awaiting decision
    expired: bool = False  # True once the signal has been encoded into a plan


@dataclass
class Thread:
    signals: list[Signal]


@dataclass
class Meaning:
    title: str
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    path: list["Step"] = field(default_factory=list)


@dataclass
class Perception:
    thread: Thread
    title: str


@dataclass
class Step:
    number: int
    tool: str
    params: dict


class Tool:
    """A persona capability that can be planned and executed.

    Subclasses declare:
      name: str               — the key used in plan steps
      requires_permission: bool — whether explicit permission is needed (default True)
      description: str        — one-line summary shown during focus
      instruction: str        — how-to shown in situation context when selected

    And implement:
      execution(**params)     — returns an async callable: async (persona) -> str
    """

    name: str = ""
    requires_permission: bool = True
    description: str = ""
    instruction: str = ""

    def execution(self, **params):
        """Return an async callable that runs this tool: async (persona) -> str."""
        raise NotImplementedError(f"{self.__class__.__name__}.execution not implemented")


class Skill:
    """A loadable knowledge document for the persona.

    Subclasses declare:
      name: str               — the key used for selection
      requires_permission: bool — (default False; skills are read-only documents)
      description: str        — one-line summary shown during focus
      instruction: str        — static usage hint (optional)

    And implement:
      execution()             — returns a callable: (persona) -> str (the full skill document)
    """

    name: str = ""
    requires_permission: bool = False
    description: str = ""
    instruction: str = ""

    def execution(self):
        """Return a callable that renders the full skill document: (persona) -> str."""
        raise NotImplementedError(f"{self.__class__.__name__}.execution not implemented")
