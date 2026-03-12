"""Mind — the persona's cognitive interface.

Exposes:
  start(persona)               — load memory, load meanings, start the tick
  trigger(persona, signal)     — accept an outside signal
  incept(persona, perception)  — inject a perception directly (bypasses understanding)
  question(persona, thought)   — inject a pre-formed thought (bypasses understand + recognize)
  block(persona) / unblock(persona) — pause/resume accepting triggers
  is_resting(persona)          — True when the conscious pipeline is fully idle
  add_meanings(persona, *meanings) — add meanings to the live list
  learn(persona, conversations) — run subconscious extraction on conversation text
  learn_from_experience(persona) — recall archived conversations, learn from them, clear memory

Memory and ego are internal — callers never touch them.
"""

from application.core.brain.data import Signal, Perception, Thought, Meaning
from application.core.brain.mind.memory import Memory
from application.core.brain.mind import meanings
from application.core import paths
from application.core.data import Persona
from application.core.exceptions import MindError
from application.platform import logger

_memories: dict[str, Memory] = {}
_blocked: set[str] = set()


def start(persona: Persona) -> None:
    """Create or restore memory, load meanings, and start the waking tick loop."""
    logger.info("Start mind", {"persona": persona})
    if persona.id not in _memories:
        all_meanings = meanings.built_in(persona) + meanings.specific_to(persona)
        _memories[persona.id] = Memory(persona, all_meanings)
    _memories[persona.id].start_thinking()


def trigger(persona: Persona, signal: Signal) -> None:
    """Accept an outside signal into the mind. Ignored when blocked."""
    logger.info("Trigger signal in mind", {"persona": persona, "signal": signal})
    if persona.id in _blocked:
        logger.warning("Received signal for trigger in mind while blocked", {"persona": persona, "signal": signal})
        return
    mem = _memories.get(persona.id)
    if mem is None:
        raise MindError(f"Mind not loaded for persona {persona.id}")
    mem.trigger(signal)


def incept(persona: Persona, perception: Perception) -> None:
    """Inject a perception directly, bypassing understanding."""
    logger.info("Incept perception in mind", {"persona": persona, "perception": perception})
    mem = _memories.get(persona.id)
    if mem is None:
        raise MindError(f"Mind not loaded for persona {persona.id}")
    mem.incept(perception)


def question(persona: Persona, thought: Thought) -> None:
    """Inject a pre-formed thought, bypassing understanding and recognition.

    The thought's signal and perception are stored directly. Deciding picks it up
    if the meaning has a path; wondering picks it up if it has a reply.
    """
    logger.info("Question from mind", {"persona": persona, "thought": thought})
    mem = _memories.get(persona.id)
    if mem is None:
        raise MindError(f"Mind not loaded for persona {persona.id}")
    mem.incept(thought.perception)
    mem.question(thought)


def block(persona: Persona) -> None:
    """Stop accepting new triggers."""
    logger.info("Blocking mind", {"persona": persona})
    _blocked.add(persona.id)


def unblock(persona: Persona) -> None:
    """Resume accepting triggers."""
    logger.info("Unblocking mind", {"persona": persona})
    _blocked.discard(persona.id)


def is_resting(persona: Persona) -> bool:
    """True when the conscious pipeline has nothing left to process."""
    logger.info("Checking if mind is resting", {"persona": persona})
    mem = _memories.get(persona.id)
    return mem.settled if mem else True


def add_meanings(persona: Persona, *new_meanings: Meaning) -> None:
    """Add meanings to the persona's live meanings list."""
    logger.info("Add meanings to mind", {"persona": persona, "meanings": [m.name for m in new_meanings]})
    mem = _memories.get(persona.id)
    if mem:
        mem.add_meanings(*new_meanings)


async def learn(persona: Persona, conversations: str) -> None:
    """Run subconscious knowledge extraction on the given conversations."""
    logger.info("Learn in mind", {"persona": persona})
    from application.core.brain.mind import subconscious as sub

    if not conversations:
        logger.warning("No conversation to learn from in mind", {"persona": persona})
        return

    await sub.person_identity(persona, conversations)
    await sub.person_traits(persona, conversations)
    await sub.wishes(persona, conversations)
    await sub.struggles(persona, conversations)
    await sub.persona_context(persona, conversations)
    await sub.synthesize_dna(persona)


async def learn_from_experience(persona: Persona) -> None:
    """Recall archived conversations, learn from them, and clear memory.

    Caller must block and wait for is_resting() before calling this.
    """
    logger.info("Learn from mind experiences", {"persona": persona})
    mem = _memories.get(persona.id)
    if mem is None:
        logger.warning("mind.learn_from_experience: no memory loaded", {"persona": persona})
        return

    # Load conversations from recap signals → history files
    conversations = []
    for signal in mem.context:
        lines = signal.content.split("\n", 1)
        filename = lines[0]
        recap = lines[1] if len(lines) > 1 else ""
        filepath = paths.history(persona.id) / filename
        content = paths.read(filepath) if filepath.exists() else ""
        if content:
            conversations.append(f"{recap}\n{content}" if recap else content)

    await learn(persona, "\n\n---\n\n".join(conversations))
    mem.clear()


def stop(persona: Persona) -> None:
    """Stop the tick loop and remove the persona's memory."""
    logger.info("Stop mind", {"persona": persona})
    _blocked.discard(persona.id)
    mem = _memories.pop(persona.id, None)
    if mem:
        mem.stop_thinking()
