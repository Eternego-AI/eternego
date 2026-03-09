"""Realize — formally group signals into perceptions.

Guard: any Signal with no perceived_as edge.
Job:   if signal has a routed_to hint → add to that perception.
       otherwise → create a new Perception.
       Self-invalidation: clears impression and meaning on modified perceptions.

prompt() → always returns None (no LLM needed).
run(None) → pure memory restructuring.
"""

from application.core.brain.data import Perception
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> None:
    return None


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    unrealized = [
        s for s in memory.signals()
        if s.role != "information"  # information signals are pipeline markers, not conversation
        and not memory.has_outgoing(s.id, "perceived_as")
    ]
    if not unrealized:
        return False

    changed = False
    for signal in unrealized:
        routed = memory.outgoing(signal.id, "routed_to")
        if routed:
            perception = routed[0]
            perception.signals.append(signal)
            # Self-invalidation: clear stale interpretation (not for proposals — confirm owns those)
            if not memory.has_outgoing(perception.id, "proposed_for"):
                perception.impression = None
                perception.meaning = None
            perception.completed = False
            logger.info("realize: added to existing perception", {
                "persona_id": persona.id,
                "signal_id": signal.id,
                "perception_id": perception.id,
            })
        else:
            perception = Perception(signals=[signal])
            memory.add_node(perception)
            logger.info("realize: new perception", {
                "persona_id": persona.id,
                "signal_id": signal.id,
                "perception_id": perception.id,
            })

        memory.add_edge(signal.id, perception.id, "perceived_as")
        changed = True

    return changed
