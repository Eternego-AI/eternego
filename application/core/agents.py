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

from application.core.brain import character, situation
from application.core.brain.memory import Memory
from application.core.brain.pulse import Pulse
from application.core.brain.signals import CapabilityRun
from application.core.data import Persona, Prompt
from application.platform.observer import Signal, subscribe, unsubscribe


class Ego:
    def __init__(self, persona: Persona):
        self.persona = persona
        self.memory = Memory(persona)

    @property
    def model(self):
        return self.persona.thinking

    @property
    def identity(self) -> list[Prompt]:
        # Persona's stable identity (cache breakpoint); situation and context
        # are dynamic and added separately so they don't invalidate the cache
        # of the stable prefix.
        blocks = [
            Prompt(role="system", content="\n\n".join([
                character.identity(self.persona),
                character.awareness(self.persona),
                character.capabilities(self.persona),
            ]),
           cache_point=True),
        ]

        situation_text = situation.prompts(self.persona.id)
        if situation_text:
            blocks.append(Prompt(role="system", content=situation_text, cache_point=True))

        blocks.append(
            Prompt(role="system", content="\n\n".join([
                character.meanings(self.persona),
                character.substrate(self.persona),
            ]),
           cache_point=True)
        )

        context = (self.memory.context or "").strip()
        if context:
            blocks.append(Prompt(role="system", content="## Recent Context\n\n" + context))

        return blocks


class Eye:
    def __init__(self, persona: Persona):
        self.persona = persona
        self.identity = [Prompt(role="system", content=character.as_eye(persona))]

    @property
    def model(self):
        return self.persona.vision


class Consultant:
    def __init__(self, persona: Persona):
        self.persona = persona
        self.identity = [Prompt(role="system", content="\n\n".join([
            character.as_consultant(persona),
            character.awareness(persona),
        ]))]

    @property
    def model(self):
        return self.persona.thinking


class Teacher:
    def __init__(self, persona: Persona):
        self.persona = persona
        # Identity is just framing — capabilities and meanings belong in the
        # user prompt at call time, since they are data about the persona
        # being taught, not about who the teacher is. No cache point on the
        # teacher prefix: teacher fires rarely (once per genuinely-new
        # situation, then never again for that situation type), so the cache
        # write overhead typically outweighs the savings on the next call
        # within the cache window.
        self.identity = [Prompt(role="system", content=character.as_teacher(persona))]

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
        executor). Routine cycle ticks/tocks and heartbeat noise don't count.
        If no activity has been captured yet (fresh restart), Living's birth
        time is the reference."""
        if seconds is None:
            seconds = self.ego.persona.idle_timeout
        latest = self.created_at
        for signal in reversed(self.signals):
            if isinstance(signal, CapabilityRun):
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
