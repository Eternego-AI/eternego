"""Recognize — match a perception's impression to a known meaning.

Guard: Perception with impression set, meaning = None, no open proposal,
       not a proposal perception itself (has no outgoing proposed_for edge).
Job:   look up impression against all known meanings (built-in + persona-specific).
       Sets perception.meaning if a match is found.
       If perception has a conversational user signal and meaning.reply is set:
         generates reply text and calls mind.reply() directly, adds assistant signal.
       If meaning has no path (plan=None): marks perception.completed immediately.
       Does nothing on no match — experience handles that case.

prompt() → returns match query (with optional reply generation) for the first pending perception.
run(data) → sets perception.meaning; delivers reply; marks completed if no-plan meaning.
"""

from application.core.brain.data import Signal
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    pending = [
        p for p in memory.perceptions()
        if p.impression is not None
        and p.meaning is None
        and not p.completed
        and not memory.has_incoming(p.id, "proposed_for")
        and not memory.has_outgoing(p.id, "proposed_for")
    ]
    if not pending:
        return None

    from application.core.brain import meanings as brain_meanings, ego
    builtin = brain_meanings.all_meanings()
    persona_specific = ego.load_persona_meanings(persona)
    all_m = [m for m in builtin + persona_specific if m.origin != "assistant"]
    if not all_m:
        return None

    perception = pending[0]
    has_conversational = any(
        s.role == "user" and s.data.get("verbosity") == "conversational"
        for s in perception.signals
    )

    logger.info("recognize: matching", {
        "persona_id": persona.id,
        "impression": (perception.impression or "")[:60],
        "conversational": has_conversational,
    })

    if has_conversational:
        options_text = "\n".join(
            f"- {m.name}: {m.definition}" + (f' [reply: "{m.reply}"]' if m.reply else "")
            for m in all_m
        )
        return (
            f"Impression: '{perception.impression}'\n\n"
            "Match this impression to the most fitting meaning below, or 'none' if nothing fits closely.\n"
            "If matched and a reply instruction is shown, generate appropriate reply text.\n\n"
            f"Meanings:\n{options_text}\n\n"
            'Return JSON: {"match": "exact_meaning_name_or_none", "reply": "reply text or empty string"}',
            "",
        )
    else:
        options_text = "\n".join(f"- {m.name}: {m.definition}" for m in all_m)
        return (
            f"Impression: '{perception.impression}'\n\n"
            "Match this impression to the most fitting meaning below, or 'none'.\n\n"
            f"Meanings:\n{options_text}\n\n"
            'Return JSON: {"match": "exact_meaning_name_or_none"}',
            "",
        )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    if data is None:
        return False

    pending = [
        p for p in memory.perceptions()
        if p.impression is not None
        and p.meaning is None
        and not p.completed
        and not memory.has_incoming(p.id, "proposed_for")
        and not memory.has_outgoing(p.id, "proposed_for")
    ]
    if not pending:
        return False

    perception = pending[0]
    from application.core.brain import meanings as brain_meanings, ego
    builtin = brain_meanings.all_meanings()
    persona_specific = ego.load_persona_meanings(persona)
    all_m = [m for m in builtin + persona_specific if m.origin != "assistant"]

    match = data.get("match", "none") if isinstance(data, dict) else "none"
    reply_text = data.get("reply", "") if isinstance(data, dict) else ""
    if not match or match == "none":
        return False

    for m in all_m:
        if m.name != match:
            continue

        perception.meaning = m.name
        logger.info("recognize: matched", {
            "persona_id": persona.id,
            "perception_id": perception.id,
            "meaning": m.name,
        })

        # Deliver reply for conversational perceptions
        has_conversational = any(
            s.role == "user" and s.data.get("verbosity") == "conversational"
            for s in perception.signals
        )
        if has_conversational and reply_text:
            # Add to perception history
            reply_sig = Signal(role="assistant", data={"content": reply_text})
            memory.add_node(reply_sig)
            perception.signals.append(reply_sig)
            memory.add_edge(reply_sig.id, perception.id, "perceived_as")
            # Deliver to person
            from application.core import registry
            mind = registry.mind(persona.id)
            if mind:
                await mind.reply(reply_text)

        # If no plan, mark completed so conclusion can archive
        if m.path is None:
            perception.completed = True

        return True

    return False
