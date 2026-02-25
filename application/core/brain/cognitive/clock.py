"""Clock — the cognitive loops that keep the persona's mind running.

tick(persona, mem, thought) is the atomic step: one thought in, one stimulus out.
start(persona, mem) launches all four loops as background tasks.

stream groups the four concurrent loops:
  understand    — stimuli from presence → perceptions into awareness
  attention     — perceptions from awareness → thoughts into mind
  conscious     — conscious thoughts → will → tick → stimulus into presence
  sub_conscious — sub-conscious thoughts → act → done
"""

from application.core.data import Persona
from application.core.brain.cognitive.data import Thought, Stimulus
from application.core.brain.cognitive.memory import Memory
from application.core.brain.cognitive import ego, memory
from application.platform import logger, processes, datetimes


async def tick(persona: Persona, mem: Memory, thought: Thought) -> Stimulus:
    """Process one thought through the persona's ego and return a new stimulus."""
    response = await ego.reason(persona, mem, thought.content)
    content = response.get("content", "") if isinstance(response, dict) else ""
    if not content:
        logger.warning("tick: model returned no content", {"persona_id": persona.id, "thread_id": thought.thread_id})
    return Stimulus(
        role="assistant",
        content=content,
        thread_id=thought.thread_id,
    )


class Stream:
    """The four cognitive loops, grouped for use by start()."""

    async def understand(self, persona: Persona, mem: Memory) -> None:
        """Continuously interpret stimuli from presence into perceptions in awareness."""
        while True:
            await mem.presence.changed.wait()
            mem.presence.changed.clear()
            stimuli = mem.presence.be()
            if stimuli:
                perceptions = await ego.understand(persona, mem, stimuli)
                if perceptions:
                    now = datetimes.now()
                    for stimulus, perception in zip(stimuli, perceptions):
                        stimulus.understood_at = now
                        mem.awareness.pay(perception)
                    await memory.save(mem, persona)
                    logger.info("understand: stimuli processed", {"persona_id": persona.id, "count": len(perceptions)})

    async def attention(self, persona: Persona, mem: Memory) -> None:
        """Continuously convert perceptions from awareness into thoughts in mind."""
        while True:
            await mem.awareness.changed.wait()
            mem.awareness.changed.clear()
            perceptions = mem.awareness.be()
            if perceptions:
                thoughts = await ego.attention(persona, mem, perceptions)
                if thoughts:
                    now = datetimes.now()
                    for perception, thought in zip(perceptions, thoughts):
                        perception.attended_at = now
                        mem.mind.keep(thought)
                    await memory.save(mem, persona)
                    logger.info("attention: perceptions attended", {"persona_id": persona.id, "count": len(thoughts)})

    async def conscious(self, persona: Persona, mem: Memory) -> None:
        """Continuously pick one conscious thought via will, tick it, and emit a stimulus."""
        while True:
            await mem.mind.conscious_changed.wait()
            mem.mind.conscious_changed.clear()
            unpicked = [t for t in mem.mind.read() if t.role != "assistant" and t.picked_at is None]
            if unpicked:
                chosen = await ego.will(persona, mem, unpicked)
                chosen.picked_at = datetimes.now()
                stimulus = await tick(persona, mem, chosen)
                chosen.done_at = datetimes.now()
                mem.presence.consider(stimulus)
                await memory.save(mem, persona)
                logger.info("conscious: thought processed", {"persona_id": persona.id, "thread_id": chosen.thread_id})

    async def sub_conscious(self, persona: Persona, mem: Memory) -> None:
        """Continuously act on each unpicked sub-conscious thought."""
        while True:
            await mem.mind.sub_conscious_changed.wait()
            mem.mind.sub_conscious_changed.clear()
            unpicked = [t for t in mem.mind.read() if t.role == "assistant" and t.picked_at is None]
            if unpicked:
                now = datetimes.now()
                for thought in unpicked:
                    thought.picked_at = now
                    # TODO: dispatch to trait abilities (act)
                    thought.done_at = datetimes.now()
                await memory.save(mem, persona)
                logger.info("sub_conscious: thoughts acknowledged", {"persona_id": persona.id, "count": len(unpicked)})


stream = Stream()


def start(persona: Persona, mem: Memory) -> None:
    """Start all four cognitive loops as background tasks for this persona."""
    processes.run_async(lambda: stream.understand(persona, mem))
    processes.run_async(lambda: stream.attention(persona, mem))
    processes.run_async(lambda: stream.conscious(persona, mem))
    processes.run_async(lambda: stream.sub_conscious(persona, mem))
    logger.info("clock: cognitive loops started", {"persona_id": persona.id})
