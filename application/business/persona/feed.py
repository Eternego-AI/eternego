"""Persona — feeding external AI history.

Imports the person's chat history from another AI provider so the persona
can learn from it. Each conversation is processed as a *past Living*: a
sandboxed Living instance whose memory holds the imported messages. The
persona's own consolidate (the work reflect does) runs on that past Living
to extract person identity / traits / wishes / struggles / persona-traits /
permissions and a carried context. Person files merge into the persona's
real disk state. The carried context is handed to the live persona as a
user-role message — "Here is fed data from {source}; you can use it" —
so the persona can decide what to do with it.

Sandboxing: past Memory uses `sandbox=True` (no disk persistence), past
Living uses `subscribe_signals=False` (no bus capture). Past Living's
operations don't touch the live persona's persistent state or signal stream.
"""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, models
from application.core.agents import Consultant, Ego, Eye, Living, Teacher
from application.core.brain.functions.reflect import consolidate
from application.core.brain.memory import Memory
from application.core.brain.pulse import Phase, Pulse
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import EngineConnectionError, ModelError
from application.platform.asyncio_worker import Worker


@dataclass
class FeedData:
    persona: Persona


async def feed(living: Living, data: str, source: str) -> Outcome[FeedData]:
    """Import external chat history into the persona.

    For each conversation in the data, build a past Living (sandboxed),
    consolidate it, then deliver the past context as a fed-data message in
    the live persona's memory."""
    persona = living.ego.persona
    bus.propose("Feeding persona", {"persona": persona, "source": source})

    class PastMemory(Memory):
        """Memory built from imported data, in process only — never reaches the
        persona's disk."""

        def _load(self) -> None:
            pass

        def _persist(self) -> None:
            pass

    class PastLiving(Living):
        """A Living that does not subscribe to the bus — its signal stream is
        isolated from the live persona's."""

        def _on_construct(self) -> None:
            pass

    try:
        conversations = await models.read_external_history(data, source)
    except ModelError as e:
        bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    try:
        for conversation in conversations:
            past_messages = []
            for m in conversation:
                role = "user" if m.get("role") == "user" else "assistant"
                content = m.get("content", "")
                past_messages.append(Message(
                    content=content,
                    prompt=Prompt(role=role, content=content),
                ))
            if not past_messages:
                continue

            past_memory = PastMemory(persona)
            for m in past_messages:
                past_memory.remember(m)

            past_ego = Ego(persona)
            past_ego.memory = past_memory

            past_pulse = Pulse(Worker())
            past_pulse.phase = Phase.NIGHT

            past_living = PastLiving(
                pulse=past_pulse,
                ego=past_ego,
                eye=Eye(persona),
                consultant=Consultant(persona),
                teacher=Teacher(persona),
            )

            try:
                await consolidate(past_living)
                past_context = (past_memory.context or "").strip()
                if past_context:
                    intro = (
                        f"Here is fed data from {source} that seems to be useful for you. "
                        f"You can use it: {past_context}"
                    )
                    living.ego.memory.remember(Message(
                        content=intro,
                        prompt=Prompt(role="user", content=intro),
                    ))
            finally:
                past_living.dispose()

        bus.broadcast("Persona fed", {"persona": persona, "source": source})
        return Outcome(success=True, message="Persona fed successfully", data=FeedData(persona=persona))

    except EngineConnectionError as e:
        bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")
