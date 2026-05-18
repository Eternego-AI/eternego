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

`Living` is the persona's runtime — pulse, memory, voices, and a mind
(the cycle of cognitive functions for the current phase). The Agent
serves a Living for a Persona.
"""

from application.core.brain import character, situation
from application.core.brain.memory import Memory
from application.core.brain.pulse import Phase, Pulse
from application.core.data import Persona, Prompt


class Ego:
    """The persona's personality — her voice. Carries the stable identity
    prompts (character, awareness, capabilities, situation, meanings,
    substrate). Memory and Recent Context live on Living now; her identity
    here is the stable prefix that doesn't change between beats."""

    def __init__(self, persona: Persona):
        self.persona = persona

    @property
    def model(self):
        return self.persona.thinking

    @property
    def identity(self) -> list[Prompt]:
        # Stable identity blocks only — each gets a cache breakpoint. Dynamic
        # state (Recent Context, conversation) is composed by Living.identity.
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

        return blocks


class Eye:
    """The persona's sight. Realize hands the eye an image and a question;
    the eye's identity (set in character.as_eye) gives it the framing it
    needs to report facts rather than narrate around them."""

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
    """The persona being-alive — the runtime state. The glue that holds
    her parts together while she's alive.

    Holds the rhythm (pulse — phase, worker, signal history, idle
    detection), the memory (what she remembers), the alive voices (ego,
    eye, consultant, teacher), and her mind (the cycle of cognitive
    functions for the current phase).

    Functions in the mind reach into Living for everything they need:
        living.ego, living.memory, living.teacher, living.eye,
        living.consultant, living.pulse.
    """

    def __init__(
        self,
        pulse: Pulse,
        ego: "Ego",
        memory: Memory,
        eye: "Eye",
        consultant: "Consultant",
        teacher: "Teacher",
    ):
        self.pulse = pulse
        self.ego = ego
        self.memory = memory
        self.eye = eye
        self.consultant = consultant
        self.teacher = teacher
        # The persona's current perception state — populated by abilities
        # that capture the screen (take_screenshot, locate, screen). Keys:
        #   "landscape": {"x", "y", "w", "h"}  — rect on default monitor (logical)
        #   "retina":    {"w", "h"}            — saved image dimensions
        # Empty until the first capture; screen refuses to act until then.
        self.view: dict = {}
        self.mind: list = []

    def phase(self, phase: Phase) -> None:
        """Shift into a phase: rebuild the mind's cycle for that phase,
        mark the pulse, and reset the felt stream. No-op if already in
        that phase. Callers that need the worker nudged do it themselves.

        Each phase has its own cycle — Morning starts the day's work,
        Day adds reflection and archiving once the work runs, Night
        stops perceiving and only closes out. Each cycle item is a
        `(name, callable)` pair — Clock walks this list every beat,
        invoking each callable with no args."""
        if self.pulse.phase == phase:
            return
        # Lazy import to break the agents↔functions cycle.
        from application.core.brain import functions
        match phase:
            case Phase.MORNING:
                self.mind = [
                    ("realize",    lambda: functions.realize(self.memory, self.ego, self.eye, self.consultant)),
                    ("recognize",  lambda: functions.recognize(self.pulse, self.memory, self.ego)),
                    ("learn",      lambda: functions.learn(self.memory, self.ego, self.teacher)),
                    ("decide",     lambda: functions.decide(self.memory, self.ego)),
                ]
            case Phase.DAY:
                self.mind = [
                    ("realize",    lambda: functions.realize(self.memory, self.ego, self.eye, self.consultant)),
                    ("recognize",  lambda: functions.recognize(self.pulse, self.memory, self.ego)),
                    ("learn",      lambda: functions.learn(self.memory, self.ego, self.teacher)),
                    ("decide",     lambda: functions.decide(self.memory, self.ego)),
                    ("reflect",    lambda: functions.reflect(self.pulse, self.memory, self.ego)),
                ]
            case Phase.NIGHT:
                self.mind = [
                    ("reflect",    lambda: functions.reflect(self.pulse, self.memory, self.ego)),
                    ("archive",    lambda: functions.archive(self.memory, self.ego)),
                ]
        self.pulse.phase = phase
        self.pulse.signals = []
