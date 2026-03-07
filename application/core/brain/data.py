"""Data — the brain's core data types.

Occurrence  — a cause+effect pair: one exchange between person and persona
Thread      — a group of related occurrences with a title, produced by realize
Perception  — a thread with impression and result, produced by understand and close
Thought     — a perception paired with a plan (list of Steps)
Step        — a single tool invocation with parameters
Tool        — base class for persona capabilities
Skill       — base class for persona knowledge documents
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime

from application.core.data import Persona, Prompt
from application.platform import datetimes


@dataclass
class Occurrence:
    cause: Prompt
    effect: Prompt
    created_at: datetime = field(default_factory=datetimes.now)
    id: str = field(default_factory=lambda: secrets.token_hex(4))


@dataclass
class Thread:
    occurrences: list[Occurrence]
    title: str = ""
    id: str = field(default_factory=lambda: secrets.token_hex(4))


@dataclass
class Perception:
    thread: Thread
    impression: str
    result: str = ""


@dataclass
class Step:
    number: int
    tool: str
    params: dict


@dataclass
class Thought:
    perception: Perception
    steps: list[Step]


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
