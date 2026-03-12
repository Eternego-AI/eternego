"""Mind — the persona's cognitive interface.

Exposes:
  start(persona)               — load memory, load meanings, start the tick
  trigger(persona, signal)     — accept an outside signal
  incept(persona, perception)  — inject a perception directly (bypasses understanding)
  block(persona) / unblock(persona) — pause/resume accepting triggers
  is_resting(persona)          — True when the conscious pipeline is fully idle
  learn(persona, conversations) — run subconscious extraction on conversation text
  learn_from_experience(persona) — recall archived conversations, learn from them, clear memory

Memory and ego are internal — callers never touch them.
"""

import asyncio

from application.core.brain.data import Signal, Perception
from application.core.brain.mind.memory import Memory
from application.core.brain.mind.meanings import all_meanings
from application.core import paths
from application.core.exceptions import MindError
from application.platform import logger

_memories: dict[str, Memory] = {}
_blocked: set[str] = set()


def start(persona) -> None:
    """Create or restore memory, load meanings, and start the waking tick loop."""
    if persona.id not in _memories:
        core_meanings = all_meanings(persona)
        _memories[persona.id] = Memory(persona, core_meanings)
        logger.info("mind.start: created memory", {"persona": persona.id})
    _memories[persona.id].start_thinking()


def trigger(persona, signal: Signal) -> None:
    """Accept an outside signal into the mind. Ignored when blocked."""
    if persona.id in _blocked:
        logger.warning("mind.trigger: blocked", {"id": signal.id})
        return
    mem = _memories.get(persona.id)
    if mem is None:
        raise MindError(f"Mind not loaded for persona {persona.id}")
    mem.trigger(signal)


def incept(persona, perception: Perception) -> None:
    """Inject a perception directly, bypassing understanding."""
    mem = _memories.get(persona.id)
    if mem is None:
        raise MindError(f"Mind not loaded for persona {persona.id}")
    mem.incept(perception)


def block(persona) -> None:
    """Stop accepting new triggers."""
    _blocked.add(persona.id)
    logger.info("mind.block", {"persona": persona.id})


def unblock(persona) -> None:
    """Resume accepting triggers."""
    _blocked.discard(persona.id)
    logger.info("mind.unblock", {"persona": persona.id})


def is_resting(persona) -> bool:
    """True when the conscious pipeline has nothing left to process."""
    mem = _memories.get(persona.id)
    return mem.settled if mem else True


async def learn(persona, conversations: str) -> None:
    """Run subconscious knowledge extraction on the given conversations."""
    from application.core.brain.mind import subconscious as sub

    if not conversations:
        logger.info("mind.learn: no conversations to process")
        return

    logger.info("mind.learn: started", {"persona": persona.id})
    await sub.person_identity(persona, conversations)
    await sub.person_traits(persona, conversations)
    await sub.wishes(persona, conversations)
    await sub.struggles(persona, conversations)
    await sub.persona_context(persona, conversations)
    await sub.synthesize_dna(persona)
    logger.info("mind.learn: finished", {"persona": persona.id})


async def learn_from_experience(persona) -> None:
    """Recall archived conversations, learn from them, and clear memory.

    Caller must block and wait for is_resting() before calling this.
    """
    mem = _memories.get(persona.id)
    if mem is None:
        logger.warning("mind.learn_from_experience: no memory loaded", {"persona": persona.id})
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


def stop(persona_id: str) -> None:
    """Stop the tick loop and remove the persona's memory."""
    _blocked.discard(persona_id)
    mem = _memories.pop(persona_id, None)
    if mem:
        mem.stop_thinking()
