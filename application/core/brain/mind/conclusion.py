"""Conclusion — archive resolved perceptions and deliver recap.

Guard: Perception that is completed AND has no planned Thought AND
       no incoming unresolved proposed_for edges.
Job:   Check if the perception had a plan (has result signals).
       If yes: one LLM call → generate recap from result signals.
               Call mind.reply(recap) if conversational.
               Call mind.archive(perception, recap=recap).
       If no:  Call mind.archive(perception) — no recap, no briefing.

prompt() → returns recap query for the first resolved perception (if had plan), else None.
run(data) → archives the perception; delivers recap if conversational.
"""

from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    resolved = _find_resolved(memory)
    if not resolved:
        return None

    perception = resolved[0]

    # If no signals at all, run() handles cleanup without LLM
    if not perception.signals:
        return None

    # Check if had a plan (has result signals)
    result_signals = [s for s in perception.signals if s.role == "result"]
    if not result_signals:
        return None  # no plan — run() archives without recap

    from application.core.brain import ego
    sig_text = ego.format_signals(perception.signals)

    return (
        f"Impression: {perception.impression}\n\n"
        f"Conversation and results:\n{sig_text}\n\n"
        "Give a one-sentence recap from your perspective of what happened.\n"
        'Return JSON: {"recap": "..."}',
        "",
    )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    resolved = _find_resolved(memory)
    if not resolved:
        return False

    perception = resolved[0]

    if not perception.signals:
        # Empty perception — clean up without archiving
        memory.remove_node(perception.id)
        return True

    result_signals = [s for s in perception.signals if s.role == "result"]
    had_plan = len(result_signals) > 0

    from application.core import registry
    mind = registry.mind(persona.id)

    if had_plan and data is not None:
        recap = data.get("recap", "") if isinstance(data, dict) else ""

        # Deliver recap for conversational perceptions
        is_conversational = any(
            s.role == "user" and s.data.get("verbosity") == "conversational"
            for s in perception.signals
        )
        if is_conversational and recap and mind:
            await mind.reply(recap)

        if mind:
            await mind.archive(perception, recap=recap or None)
    else:
        # No plan (conversational meaning) or no data — archive without recap
        if mind:
            await mind.archive(perception)

    logger.info("conclusion: archived", {
        "persona_id": persona.id,
        "perception_id": perception.id,
        "had_plan": had_plan,
    })
    return True


def _find_resolved(memory: Memory) -> list:
    resolved = []
    for p in memory.perceptions():
        if not p.completed:
            continue
        has_thought = any(t for t in memory.thoughts() if t.perception_id == p.id)
        if has_thought:
            continue
        has_open_proposal = any(
            prop for prop in memory.perceptions()
            if memory.has_outgoing(prop.id, "proposed_for")
            and memory.outgoing(prop.id, "proposed_for") == [p]
            and not prop.completed
        )
        if has_open_proposal:
            continue
        resolved.append(p)
    return resolved
