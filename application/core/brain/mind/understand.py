"""Understand — produce an impression for a perception.

Guard: any Perception with impression = None (and at least one signal).
Job:   one LLM call per tick round — reads signals, returns impression string.

prompt() → returns impression query for the first pending perception.
run(data) → sets perception.impression from {"impression": "..."}.
"""

from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    pending = [
        p for p in memory.perceptions()
        if p.impression is None and p.signals
    ]
    if not pending:
        return None

    from application.core.brain import ego
    perception = pending[0]
    sig_text = ego.format_signals(perception.signals)

    return (
        f"Conversation:\n{sig_text}\n\n"
        "Give a concise 2-6 word label for the core intent of this conversation. "
        "Examples: 'greeting', 'setting a reminder', 'building a web app', 'checking the weather'. "
        "Be specific enough to distinguish it from other conversations. No full sentences.\n"
        'Return JSON: {"impression": "..."}',
        "",
    )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    if data is None:
        return False

    pending = [
        p for p in memory.perceptions()
        if p.impression is None and p.signals
    ]
    if not pending:
        return False

    perception = pending[0]
    impression = data.get("impression") if isinstance(data, dict) else None
    if impression:
        perception.impression = impression
        logger.info("understand: impression set", {
            "persona_id": persona.id,
            "perception_id": perception.id,
            "impression": impression[:60],
        })
        return True
    return False
