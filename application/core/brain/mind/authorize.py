"""Authorize — route incoming signals to known open perceptions.

Guard: any Signal with no outgoing edges (no perceived_as, no routed_to).
Job:   determine if the signal continues an existing perception.
       Adds a routed_to hint edge if matched; realize confirms formally.

prompt() → returns route query for the first unrouted signal, or None.
run(data) → applies routing decision {"index": N or null}.
"""

from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    unrouted = [
        s for s in memory.signals()
        if s.role == "user"  # only user signals need routing; information signals are standalone
        and not memory.has_outgoing(s.id, "perceived_as")
        and not memory.has_outgoing(s.id, "routed_to")
    ]
    if not unrouted:
        return None

    open_perceptions = [p for p in memory.perceptions() if not p.completed]
    if not open_perceptions:
        return None  # nothing to route to; realize will create new perceptions

    signal = unrouted[0]
    sig_text = f"New signal [{signal.created_at.strftime('%H:%M')}]: {signal.data.get('content', '')[:200]}"

    lines = [
        sig_text,
        "",
        "Existing open perceptions:",
    ]
    for i, p in enumerate(open_perceptions):
        last_content = ""
        if p.signals:
            last = p.signals[-1]
            last_content = last.data.get("content") or last.data.get("output", "")
        last_content = last_content[:80]
        imp = f" — {p.impression}" if p.impression else ""
        lines.append(f"{i}. {last_content}{imp}")

    lines += [
        "",
        "Does this signal continue one of the existing perceptions, or is it a new topic?",
        'Return JSON: {"index": <0-based index or null>}',
        "null means it starts a new perception.",
    ]

    logger.info("authorize: routing signal", {
        "persona_id": persona.id,
        "signal_id": signal.id,
        "open_perceptions": len(open_perceptions),
    })

    return "\n".join(lines), ""


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    if data is None:
        return False

    unrouted = [
        s for s in memory.signals()
        if s.role == "user"
        and not memory.has_outgoing(s.id, "perceived_as")
        and not memory.has_outgoing(s.id, "routed_to")
    ]
    if not unrouted:
        return False

    open_perceptions = [p for p in memory.perceptions() if not p.completed]
    signal = unrouted[0]
    index = data.get("index") if isinstance(data, dict) else None

    if isinstance(index, int) and 0 <= index < len(open_perceptions):
        target = open_perceptions[index]
        memory.add_edge(signal.id, target.id, "routed_to")
        logger.info("authorize: routed signal", {
            "persona_id": persona.id,
            "signal_id": signal.id,
            "perception_id": target.id,
        })
        return True

    return False  # null index — realize will create a new perception
