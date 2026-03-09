"""Data — the brain's core data types.

Signal     — the atomic unit: role + data dict + processed_at
Perception — a group of related signals with an evolving interpretation
Thought    — a plan (perception_id + ordered steps + authorized flag)
PathStep   — one step in a meaning's path template (tool + param descriptions + section)
Meaning    — a pre-defined intent (impression → reply + path + skills + tools)
Step       — a single tool invocation with parameters
Tool       — base class for persona capabilities
Skill      — base class for persona knowledge documents
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime

from application.platform import datetimes


@dataclass
class Signal:
    """Atomic cognitive unit.

    Roles:
      user        — incoming message from the person
      assistant   — raw LLM output or outgoing text
      result      — tool execution output
      information — pipeline marker (archive_done, person_done, etc.)

    data keys vary by role:
      user:        {content, verbosity}
      assistant:   {content}
      result:      {tool, output, success}
      information: {type, ...}

    processed_at is set by the module responsible for handling this signal.
    processed_at=None means "not yet handled by its owner module".
    """
    role: str
    data: dict
    id: str = field(default_factory=lambda: secrets.token_hex(4))
    created_at: datetime = field(default_factory=datetimes.now)
    processed_at: datetime | None = None


@dataclass
class Perception:
    signals: list[Signal]
    id: str = field(default_factory=lambda: secrets.token_hex(4))
    created_at: datetime = field(default_factory=datetimes.now)
    impression: str | None = None    # set by understand
    meaning: str | None = None       # meaning name; set by recognize or confirm
    completed: bool = False          # set by think (end signal) or recognize (no-plan meaning)


@dataclass
class PathStep:
    """One step in a meaning's path template.

    params maps param names to descriptions (for the model to fill).
    Special values (never sent to model):
      "$perception_id" — injected by think
      "$tool_output"   — injected by do with previous step's output (within same section)

    section groups steps into checkpoint groups. Steps with the same section number
    run together. After a section completes, think sees the results before planning
    the next section.
    """
    tool: str
    params: dict  # param_name → description or special value
    section: int = 1


class Meaning:
    """A pre-defined intent — what a conversation means and how to handle it.

    Subclasses declare class-level attributes and assign a module-level instance:

        class _Greeting(Meaning):
            name = "greeting"
            definition = "The person is saying hello"
            reply = "respond warmly and naturally"
            path = None  # no execution needed, reply is enough

        meaning = _Greeting()

    reply: instruction for what to say when meaning is recognized.
           Delivered only if the perception contains a conversational user signal.
           None = no immediate reply (e.g. silent routines with no user signal).

    path: None = conversational (no execution, reply handles everything)
          list[PathStep] = action meaning (executor runs the steps)

    origin controls lifecycle:
        "system"    — built-in, always available
        "user"      — confirmed by the person, active for recognition
        "assistant" — proposed but not yet confirmed; excluded from recognition
    """

    name: str = ""
    definition: str = ""
    purpose: str = ""
    reply: str | None = None
    tools: list[str] = []
    skills: list[str] = []
    path: "list[PathStep] | None" = None
    origin: str = "system"

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", self.__class__.name)
        self.definition = kwargs.get("definition", self.__class__.definition)
        self.purpose = kwargs.get("purpose", self.__class__.purpose)
        self.reply = kwargs.get("reply", self.__class__.reply)
        self.tools = list(kwargs.get("tools", self.__class__.tools or []))
        self.skills = list(kwargs.get("skills", self.__class__.skills or []))
        path_val = kwargs.get("path", self.__class__.path)
        self.path = list(path_val) if path_val is not None else None
        self.origin = kwargs.get("origin", self.__class__.origin)


@dataclass
class Step:
    number: int
    tool: str
    params: dict


@dataclass
class Thought:
    perception_id: str
    steps: list[Step]
    id: str = field(default_factory=lambda: secrets.token_hex(4))
    created_at: datetime = field(default_factory=datetimes.now)
    authorized: bool = False
    pending_tools: list[str] = field(default_factory=list)  # tools awaiting permission
    completed_at: datetime | None = None


class Tool:
    """A persona capability that can be planned and executed.

    Subclasses declare:
      name: str               — the key used in plan steps
      requires_permission: bool — whether explicit permission is needed (default True)
      meaning_only: bool      — excluded from all_tools() if True; only available via meanings
      description: str        — one-line summary shown during focus
      instruction: str        — how-to shown in situation context when selected

    And implement:
      execution(**params)     — returns an async callable: async (persona) -> str
    """

    name: str = ""
    requires_permission: bool = True
    meaning_only: bool = False
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
