"""Confirm — detect whether a person confirmed, rejected, or is still discussing a proposal.

Guard: a proposal Perception (has outgoing proposed_for edge) with a user reply.
Job:   LLM call — determine confirmed / rejected / discussing.
       Confirmed → promote meaning origin "assistant" → "user", set original.meaning.
       Rejected / discussing → reset original impression and meaning for re-processing.

prompt() → returns confirm query for the first proposal with a user reply.
run(data) → applies outcome {"outcome": "confirmed" | "rejected" | "discussing"}.
"""

from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    proposals = [
        p for p in memory.perceptions()
        if memory.has_outgoing(p.id, "proposed_for")
        and _has_user_reply(p)
    ]
    if not proposals:
        return None

    from application.core.brain import ego
    proposal = proposals[0]
    sig_text = ego.format_signals(proposal.signals)

    logger.info("confirm: checking proposal", {
        "persona_id": persona.id,
        "proposal_id": proposal.id,
    })

    return (
        f"Conversation:\n{sig_text}\n\n"
        "I proposed a plan to the person. Based on their reply, did they:\n"
        "- confirm (agreed to the plan)\n"
        "- reject (said no or wants something different)\n"
        "- discussing (still asking questions or unclear)\n"
        'Return JSON: {"outcome": "confirmed" | "rejected" | "discussing"}',
        "",
    )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    if data is None:
        return False

    proposals = [
        p for p in memory.perceptions()
        if memory.has_outgoing(p.id, "proposed_for")
        and _has_user_reply(p)
    ]
    if not proposals:
        return False

    proposal = proposals[0]
    originals = memory.outgoing(proposal.id, "proposed_for")
    if not originals:
        return False

    original = originals[0]
    outcome = data.get("outcome", "discussing") if isinstance(data, dict) else "discussing"
    if outcome not in ("confirmed", "rejected", "discussing"):
        outcome = "discussing"

    logger.info("confirm: outcome", {
        "persona_id": persona.id,
        "outcome": outcome,
        "proposal_id": proposal.id,
    })

    if outcome == "confirmed":
        pending_name = proposal.meaning
        if pending_name:
            from application.core import paths
            from application.core.brain.mind.experience import _load_meaning_file
            meaning_obj = _load_meaning_file(persona, pending_name)
            if meaning_obj:
                meaning_obj.origin = "user"
                paths.save_persona_meaning(persona.id, meaning_obj)
            original.meaning = pending_name
            logger.info("confirm: meaning promoted", {
                "persona_id": persona.id,
                "meaning": pending_name,
            })
    else:
        # Rejected or discussing: reset so original re-enters the loop
        original.impression = None
        original.meaning = None

    proposal.completed = True
    return True


def _has_user_reply(proposal) -> bool:
    return any(s.role == "user" for s in proposal.signals)
