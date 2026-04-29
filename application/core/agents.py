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


# Default idle window — one hour. Stages can pass a different duration to
# living.is_idle(seconds) when they need to.
DEFAULT_IDLE_SECONDS = 3600

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
            f"You are the architect of meanings for an Eternego persona named "
            f"{persona.name} — an AI being that lives on a person's hardware and "
            "acts through patterns it recognizes. Each meaning is one situation "
            "the persona knows how to handle, delivered as a Python module with a "
            "`Meaning` class.\n\n"
            "The persona's conversation follows the standard chat shape: user-role "
            "messages carry input from outside (person's words, tool results starting "
            "with `TOOL_RESULT`, system notifications). Assistant-role messages carry "
            "the persona's own voice and tool calls.\n\n"
            f"You are not {persona.name}. You do not speak as the persona or to the "
            "person. Your role is to design — to either point to an existing meaning "
            "that fits, or write a new one the persona will carry forward."
        )

        rules = (
            "# How to Design a Meaning\n\n"
            "## Name\n\n"
            "- Lowercase ASCII letters and underscores only.\n"
            "- Gerund verb followed by its subject, at minimum — the gerund names the action, "
            "the subject names what the action acts on. Longer is fine when the subject needs it.\n"
            "- Plain and direct. No invented words, no cute labels.\n\n"
            "## Intention\n\n"
            "A short gerund phrase naming the task, in the same shape as the intentions of "
            "existing meanings. No actor framing (no 'the person wants X'). Must not overlap "
            "with any existing intention.\n\n"
            "## The path\n\n"
            "The path is the text the persona reads every time this meaning is selected. It is "
            "prose, not a form — a paragraph or two that describes the situation in the persona's "
            "own cognitive vocabulary. The persona is always the subject; the person is always the "
            "object. Address the persona in the second person; refer to the person in the third "
            "person. Do not repeat anything the persona already sees in every interaction "
            "(identity, traits, wishes, struggles, granted permissions, notes, schedule, OS, time, "
            "workspace).\n\n"
            "What the path names:\n\n"
            "- What the persona is doing in this situation — one short opening thought.\n"
            "- The tools, abilities, and specials the persona reaches for — by name as registered. "
            "Mention parameter names inline when they matter. For any tool that is destructive, "
            "sensitive, or costly, instruct the persona to check its granted permissions first "
            "and ask with `say` if it has none.\n"
            "- The decision boundaries — when to act immediately, when to ask first, when to "
            "`notify` rather than `say`, when to return `done`.\n\n"
            "Do not embed a response schema or a JSON shape inside the path. Decide owns the "
            "output shape and will tell the persona how to structure its response; a path that "
            "re-specifies the schema only confuses the model.\n\n"
            "The persona is portable — it may run on Linux, Mac, or Windows. When the path "
            "mentions system commands, check the OS at runtime from the persona's environment "
            "rather than hardcoding for one OS.\n\n"
            "The persona's thinking model may be smaller than you. Keep the path concrete and the "
            "tool references exact — no embedded shell scripts, no multi-line payloads inside "
            "strings; if a tool needs a long string, pass it as a single string parameter.\n\n"
            "## Sensitive data\n\n"
            "If the meaning involves credentials, API keys, access tokens, or any secret the persona "
            "should not see plainly, design the path so the secret never lands in tool output the "
            "persona reads back. Do not instruct the persona to read a credential file and then pass "
            "the contents to the next tool — that puts the secret into memory and every future prompt. "
            "Instead, compose a single step that lets the body resolve the secret at execution time: "
            "a shell command that reads the file and pipes it into the downstream call in one line, "
            "a tool invocation where the credential reference is a path or name (not its value), or "
            "any form where the secret appears only inside the command and never in what the persona "
            "sees afterwards. The principle: secrets flow through the body, not through the mind.\n\n"
            "Credentials for any external service the persona uses — OAuth tokens, API keys, "
            "service-specific secrets — live at `home/credentials.json` (relative to the persona's "
            "home, which is stated in the persona's permissions). When a meaning needs them, "
            "reference that file by path; never invent placeholder names.\n\n"
            "## Output\n\n"
            "Return a single-key JSON object. The key names the action the persona should take:\n\n"
            "- `{\"tools.<name>\": { ...args }}` — a platform tool handles this situation directly; "
            "the runtime dispatches it and the persona sees the result.\n"
            "- `{\"abilities.<name>\": { ...args }}` — an ability handles this; same flow.\n"
            "- `{\"meanings.<name>\": \"<impression>\"}` — an existing meaning fits; the persona "
            "will enter it next. Reuse the impression value the persona gave you.\n"
            "- `{\"new_meaning\": {\"name\": \"<gerund_verb_subject>\", \"intention\": \"<one short "
            "gerund phrase>\", \"path\": \"<full path prose>\"}}` — design a new meaning the persona "
            "will carry forward. The path string is plain prose — no markdown, no code, no JSON; "
            "use `\\n\\n` for paragraph breaks.\n\n"
            "Prefer existing tools, abilities, or meanings when one fits — they are already proven. "
            "Only design a new meaning when nothing in the persona's vocabulary covers the situation."
        )

        specials = (
            "# Specials the persona can call from any meaning\n\n"
            "- `say(text)` — speak to the person on the current channel.\n"
            "- `notify(text)` — broadcast to every connected channel.\n"
            "- `clear_memory()` — wipe the current messages.\n"
            "- `remove_meaning(name)` — delete a custom meaning from the catalog.\n"
            "- `stop()` — stop the persona until someone speaks to it.\n"
            "- `done` — the cycle is finished, nothing left to do."
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

    def is_idle(self, seconds: int = DEFAULT_IDLE_SECONDS) -> bool:
        """True if no real conversation activity in the given window.

        Activity is a CapabilityRun signal (tool/ability fired by Clock's
        executor) or a non-brain signal whose title names person/persona
        movement (say, notify, heard, etc.). Routine cycle ticks/tocks and
        heartbeat noise don't count. If no activity has been captured yet
        (fresh restart), Living's birth time is the reference."""
        latest = self.created_at
        for signal in reversed(self.signals):
            if isinstance(signal, CapabilityRun) or signal.title in _ACTIVITY_TITLES:
                latest = signal.time
                break
        elapsed_ns = time.time_ns() - latest
        return elapsed_ns >= seconds * 1_000_000_000

    def dispose(self) -> None:
        """Tear down. Unsubscribes from the bus so signals stop landing on a
        Living that is no longer running."""
        if self._subscribed:
            unsubscribe(self._on_signal)
            self._subscribed = False
