"""Mind — the persona's cognitive interface.

Module function load() creates or restores a Memory, registers it, and starts thinking.
Memory class holds the persistent graph — all thinking modules operate on it.
"""

from application.core.brain.mind.memory import Memory

__all__ = ["Memory", "load"]


def load(persona) -> Memory:
    """Create or restore a Memory for this persona, register it, and start thinking."""
    from application.core import registry
    from application.core.brain.meanings import all_meanings

    meanings = all_meanings(persona)
    memory = Memory(persona, meanings)
    registry.save(persona, memory)
    memory.start_thinking()
    return memory
