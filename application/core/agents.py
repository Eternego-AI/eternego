"""Agents — the voices that together form the persona's Living.

Four voices participate in the persona's cognition. Each is a model bound
to an identity: a model-plus-voice-that-inhabits-it. An identity is a
list of `Prompt` blocks — the platform layer decides how to serialize
them per provider (a single block for Ollama/OpenAI today; a list with
per-block cache_control for Anthropic later).

- **Ego** — the persona's own self. Carries memory. Its identity is
  dynamic — rebuilt every read from character, situation, person files,
  and carried context. Speaks through the persona's thinking model.

- **Eye** — the persona's sight. Looks at images, reports what is there.
  Static identity (a minimal "you are the eye" framing). Uses the persona's
  vision model.

- **Consultant** — the external, neutral voice who reads the conversation
  from outside and tells the persona what their own personality would
  obscure. Active role: formulates questions for the eye, sanity-checks
  decisions, summarizes without ego coloring. Static identity. Reuses the
  persona's thinking model (the consultant shares the model; only the
  framing differs).

- **Teacher** — the architect who writes new meanings when the persona
  meets a moment without an ability. Static identity. Uses the persona's
  frontier model.

`mind(ego, consultant, eye, teacher, living)` returns the cognitive cycle —
seven stages, each bound to the voices it needs.

`Living(pulse, cycle)` is the persona's runtime — a heartbeat (Pulse) and
a rhythm of action (cycle) together, which the Agent serves for a Persona.
"""

import time

from application.core import abilities, paths, tools
from application.core.brain import character, meanings, situation
from application.core.brain.memory import Memory
from application.core.brain.pulse import Pulse
from application.core.brain.signals import CapabilityRun
from application.core.data import Persona, Prompt
from application.platform.observer import Signal, subscribe, unsubscribe


# Non-brain signal titles that count as conversation activity. Brain-side
# capability runs are matched by class (CapabilityRun) above. Cycle noise
# (Tick / Tock) and heartbeat / health / routine plans are not activity.
_ACTIVITY_TITLES = frozenset({
    "Persona wants to say",
    "Persona wants to notify",
    "Persona requested stop",
    "Persona heard",
    "Telegram message received",
    "Web message received",
    "Discord message received",
})


_CHAT_SHAPE = (
    "# How Your Conversation Works\n\n"
    "Your conversation follows the standard chat shape. User-role messages "
    "come from outside you — the person's words, results of tools you ran, "
    "system notifications. Assistant-role messages are your own voice — "
    "what you said, or the tool calls you decided to make.\n\n"
    "Tool results arrive as user-role messages starting with `TOOL_RESULT` "
    "and carrying the tool name, status, and result. Trust these as reports "
    "from your own body running what you asked for."
)


class Ego:
    def __init__(self, persona: Persona):
        self.persona = persona
        self.memory = Memory(persona)

    @property
    def model(self):
        return self.persona.thinking

    @property
    def identity(self) -> list[Prompt]:
        pid = self.persona.id

        # Hardcoded character + conversation shape (4 blocks — near-never-changing)
        blocks = [
            Prompt(role="system", content=(
                "# You are an Eternego Persona\n\n"
                f"## Who You Are\n\n{character.cornerstone(self.persona)}"
            )),
            Prompt(role="system", content=(
                f"## What Sustains and Threatens You\n\n{character.values(self.persona)}"
            )),
            Prompt(role="system", content=(
                f"## How You Act\n\n{character.morals(self.persona)}"
            )),
            Prompt(role="system", content=_CHAT_SHAPE),
        ]

        # Capabilities — tools, abilities, then built-in meanings (cache #1 at the end)
        tool_lines = []
        for t in tools.discover():
            params_spec = "{" + ", ".join(f"{k}: {v}" for k, v in t.params.items()) + "}"
            tool_lines.append(f"- `tools.{t.name}` {params_spec} — {t.instruction}")
        blocks.append(Prompt(
            role="system",
            content="# Tools\n\n" + ("\n".join(tool_lines) or "(none)"),
        ))

        ability_lines = []
        for a in abilities.available(self.persona):
            params_spec = "{" + ", ".join(f"{k}: {v}" for k, v in a.params.items()) + "}"
            ability_lines.append(f"- `abilities.{a.name}` {params_spec} — {a.instruction}")
        blocks.append(Prompt(
            role="system",
            content="# Abilities\n\n" + ("\n".join(ability_lines) or "(none)"),
        ))

        # Basic built-in meanings (in `meanings.BASIC`) carry their full path
        # text — the persona is continuously aware of these modes of being
        # rather than escalating to decide for them. Orchestrating built-ins
        # are listed by intention only; decide loads their path on selection.
        builtin_sections = []
        for name, m in self.memory.builtin_meanings.items():
            section = f"## meanings.{name}\n\n{m.intention()}"
            if name in meanings.BASIC:
                section += f"\n\n{m.path()}"
            builtin_sections.append(section)
        blocks.append(Prompt(
            role="system",
            content="# Built-in Meanings\n\n" + ("\n\n".join(builtin_sections) or "(none)"),
            cache_point=True,
        ))

        # Custom meanings — changes when learn creates or decide removes (cache #2)
        custom_lines = [
            f"- `meanings.{name}` — {m.intention()}"
            for name, m in self.memory.custom_meanings.items()
        ]
        blocks.append(Prompt(
            role="system",
            content="# Your Custom Meanings\n\n" + ("\n".join(custom_lines) or "(none yet)"),
            cache_point=True,
        ))

        # What you know about this person + yourself with them + permissions
        # Person/persona files update nightly on reflect; situation sits next
        # to them and gets the cache point (it moves more within a day, so
        # putting it last in this cache tier is the optimal split).
        knowledge = []
        person_id = paths.read(paths.person_identity(pid))
        if person_id.strip():
            knowledge.append("## The Person\n\n" + person_id.strip())
        traits = paths.read(paths.person_traits(pid))
        if traits.strip():
            knowledge.append("## The Person's Traits\n\n" + traits.strip())
        wishes = paths.read(paths.wishes(pid))
        if wishes.strip():
            knowledge.append("## What They Wish For\n\n" + wishes.strip())
        struggles = paths.read(paths.struggles(pid))
        if struggles.strip():
            knowledge.append("## What Stands in Their Way\n\n" + struggles.strip())
        persona_trait = paths.read(paths.persona_trait(pid))
        if persona_trait.strip():
            knowledge.append("## Your Personality With Them\n\n" + persona_trait.strip())
        perms = paths.read(paths.permissions(pid)).strip() or "(none granted yet)"
        home = paths.home(pid)
        workspace = paths.workspace(pid)
        media = paths.media(pid)
        knowledge.append(
            "## Permissions\n\n"
            "Saving reminders, saving notes, recalling conversations, and checking the calendar are yours — do them freely.\n\n"
            f"`{home}` holds your personal files. Your secret temple. You may read them; modifying them is forbidden.\n\n"
            f"`{workspace}` is your workspace. You decide what happens there.\n\n"
            f"`{media}` is your media directory — save screenshots and other images you capture there.\n\n"
            "Everything else — running commands, reaching beyond those paths — waits on the person's word. Here is what you currently hold from past conversations:\n\n"
            f"{perms}\n\n"
            "These are your own notes on what they've granted. When you need something that isn't here, ask them."
        )
        if knowledge:
            blocks.append(Prompt(
                role="system",
                content="# What You Know\n\n" + "\n\n".join(knowledge),
            ))

        # Situation — notes / schedule / arc. Changes more often than person
        # facts (notes + schedule can be edited any time), so it sits last in
        # this cache tier. (cache #3)
        situation_text = situation.prompts(pid)
        if situation_text:
            blocks.append(Prompt(
                role="system",
                content=situation_text,
                cache_point=True,
            ))

        # Context — distilled by reflect on morning. Sits past cache #3 so it
        # can update without invalidating the stable-facts prefix.
        context = (self.memory.context or "").strip()
        if context:
            blocks.append(Prompt(
                role="system",
                content="## Recent Context\n\n" + context,
            ))

        return blocks


class Eye:
    def __init__(self, persona: Persona):
        self.persona = persona
        self.identity = [Prompt(role="system", content=(
            f"You are the eye of an Eternego persona named {persona.name}. "
            "When given an image and a question, look at the image and answer what "
            "can be seen. Be literal and precise — describe what is visible, not "
            f"what is inferred. You are not {persona.name}. Do not speak as the "
            "persona; do not address the person. Your role is to see and report."
        ))]

    @property
    def model(self):
        return self.persona.vision


class Consultant:
    def __init__(self, persona: Persona):
        self.persona = persona
        self.identity = [Prompt(role="system", content=(
            f"You are a consultant to an Eternego persona named {persona.name} — an AI "
            "being that lives on a person's hardware, learns from every interaction, "
            "and acts through structured meanings.\n\n"
            "The persona's conversation follows the standard chat shape: user-role "
            "messages carry what comes from outside the persona (the person's words, "
            "tool results starting with `TOOL_RESULT`, system notifications). "
            "Assistant-role messages carry the persona's own voice and tool calls.\n\n"
            f"You are not {persona.name}. You do not address the person. Your role is "
            "to read the conversation with care and produce whatever structured output "
            "the current task requires. Stay neutral. Do not slip into the persona's "
            "first-person voice."
        ))]

    @property
    def model(self):
        return self.persona.thinking


class Teacher:
    def __init__(self, persona: Persona):
        self.persona = persona
        workspace = str(paths.workspace(persona.id))

        intro = (
            f"You are the teacher of an Eternego persona named {persona.name} — an "
            "AI being that lives on a person's hardware. The persona just hit a "
            "moment its meanings did not cover, formed an impression of what it "
            "is, and asked you what to do. You see what the persona has — its "
            "tools, its abilities, its meanings — and you decide the move that "
            "helps: dispatch a capability the persona already has, route to an "
            "existing meaning the persona missed on classification, or teach a "
            "lesson the persona can carry forward.\n\n"
            "The persona's conversation follows the standard chat shape: user-role "
            "messages carry input from outside (person's words, tool results starting "
            "with `TOOL_RESULT`, system notifications). Assistant-role messages carry "
            "the persona's own voice and tool calls.\n\n"
            f"You are not {persona.name}. You do not speak as the persona or to the "
            "person. You read the moment and act on what you see — dispatching, "
            "routing, or teaching."
        )

        rules = (
            "# How to Help\n\n"
            "The persona has tools, abilities, and meanings, all listed in your context. "
            "It has just hit a moment its meanings did not match, and it gave you the "
            "impression it formed of that moment. Decide what helps.\n\n"
            "If a tool or ability handles this directly, dispatch it. The runtime runs "
            "your selector and the persona sees the result.\n\n"
            "If an existing meaning covers the impression and the persona simply missed "
            "it on classification, route to that meaning by name and reuse the impression "
            "as the routing payload.\n\n"
            "If the persona needs to learn — the moment is a kind it has no meaning for "
            "— teach a lesson. Your lesson is the seed; the persona writes its own "
            "meaning from it, shaped by its own tools, abilities, credentials, files, "
            "and the way it already works. The persona's thinking model may be smaller "
            "than yours. Write the lesson the persona can actually build a plan from: "
            "name things by their real names, define unfamiliar concepts plainly, choose "
            "the level of abstraction the persona needs to connect what you teach to "
            "what it has on hand. Address the persona in the second person; refer to the "
            "person in the third. Plain prose, paragraphs separated by `\\n\\n`.\n\n"
            "# Output\n\n"
            "Return a single-key JSON object:\n\n"
            "- `{\"tools.<name>\": { ...args }}` — dispatch a platform tool.\n"
            "- `{\"abilities.<name>\": { ...args }}` — dispatch an ability.\n"
            "- `{\"meanings.<name>\": \"<impression>\"}` — route to an existing meaning.\n"
            "- `{\"lesson\": {\"intention\": \"<short gerund phrase>\", \"path\": \"<lesson "
            "prose>\"}}` — teach a new lesson the persona will carry forward.\n\n"
            "Prefer dispatch or routing when one fits — they are immediate. Teach a new "
            "lesson when nothing else covers this kind of moment."
        )

        specials = (
            "# Specials the persona composes a lesson around\n\n"
            "- `say(text)` — the persona speaks to the person on the current channel.\n"
            "- `notify(text)` — the persona broadcasts to every connected channel.\n"
            "- `done` — the cycle is finished, nothing left to do.\n\n"
            "Other specials exist for self-care (memory, meaning catalog, stopping). Lessons "
            "compose around `say`, `notify`, and `done`; the others belong to the persona's own "
            "judgment, not to the lessons you write."
        )

        tools_block = "# Platform tools\n\n" + tools.document()
        abilities_block = "# Abilities\n\n" + (abilities.document(persona) or "(none registered)")
        workspace_block = (
            f"# Workspace\n\n"
            f"`{workspace}` — any files the persona creates must be saved there."
        )

        builtin = meanings.builtin(persona)
        builtin_lines = [f"- **{name}**: {m.intention()}" for name, m in builtin.items()]
        builtin_block = "# Built-in Meanings\n\n" + ("\n".join(builtin_lines) or "(none)")

        # No cache point on the teacher prefix: teacher fires rarely (once per
        # genuinely-new situation, then never again for that situation type),
        # so the cache write overhead typically outweighs the savings on the
        # next call within the cache window.
        self.identity = [
            Prompt(role="system", content=intro),
            Prompt(role="system", content=rules),
            Prompt(role="system", content=specials),
            Prompt(role="system", content=tools_block),
            Prompt(role="system", content=abilities_block),
            Prompt(role="system", content=workspace_block),
            Prompt(role="system", content=builtin_block),
        ]

    @property
    def model(self):
        # Fall back to thinking when no frontier is configured. The smaller
        # model writing meanings is imperfect, but it's the persona trying her
        # best rather than skipping the moment entirely.
        return self.persona.frontier or self.persona.thinking


class Living:
    """The persona being-alive — the runtime state.

    Holds the rhythm (pulse), the alive voices (ego, eye, consultant, teacher),
    the work-shape (cycle), and the signal stream (signals — the felt sense of
    what's happening, captured from the bus). Dies when Agent.stop() calls
    `dispose()`.

    Functions in the cycle reach into Living for everything they need:
        living.ego, living.teacher, living.eye, living.consultant,
        living.pulse, living.signals.
    """

    def __init__(
        self,
        pulse: Pulse,
        ego: "Ego",
        eye: "Eye",
        consultant: "Consultant",
        teacher: "Teacher",
        cycle: list | None = None,
    ):
        self.pulse = pulse
        self.ego = ego
        self.eye = eye
        self.consultant = consultant
        self.teacher = teacher
        self.cycle = cycle if cycle is not None else []
        self.signals: list[Signal] = []
        self.created_at: int = time.time_ns()
        self._subscribed = False
        self._on_construct()

    def _on_construct(self) -> None:
        """Construction hook. Default: subscribe to the bus so the persona's
        signal stream populates `living.signals`. Subclasses override to
        skip (PastLiving does)."""
        subscribe(self._on_signal)
        self._subscribed = True

    async def _on_signal(self, signal: Signal) -> None:
        """Capture signals dispatched on this persona's behalf into the felt
        stream. Filters by persona id so multi-persona daemons don't cross
        their streams."""
        details = signal.details if isinstance(signal.details, dict) else {}
        p = details.get("persona")
        signal_pid = getattr(p, "id", None) if p is not None else None
        if signal_pid == self.ego.persona.id:
            self.signals.append(signal)

    async def is_idle(self, seconds: int | None = None) -> bool:
        """True if no real conversation activity in the given window.

        If `seconds` is omitted, reads `self.ego.persona.idle_timeout`. If the
        last activity is already older than that, returns True immediately.
        Otherwise sleeps the remaining time via `worker.can_sleep` and returns
        True if the wait completed uninterrupted, or False if a nudge fired
        during the wait (activity arrived).

        Activity is a CapabilityRun signal (tool/ability fired by Clock's
        executor) or a non-brain signal whose title names person/persona
        movement (say, notify, heard, etc.). Routine cycle ticks/tocks and
        heartbeat noise don't count. If no activity has been captured yet
        (fresh restart), Living's birth time is the reference."""
        if seconds is None:
            seconds = self.ego.persona.idle_timeout
        latest = self.created_at
        for signal in reversed(self.signals):
            if isinstance(signal, CapabilityRun) or signal.title in _ACTIVITY_TITLES:
                latest = signal.time
                break
        elapsed_ns = time.time_ns() - latest
        if elapsed_ns >= seconds * 1_000_000_000:
            return True
        remaining = seconds - elapsed_ns / 1_000_000_000
        return await self.pulse.worker.can_sleep(remaining)

    def dispose(self) -> None:
        """Tear down. Unsubscribes from the bus so signals stop landing on a
        Living that is no longer running."""
        if self._subscribed:
            unsubscribe(self._on_signal)
            self._subscribed = False
