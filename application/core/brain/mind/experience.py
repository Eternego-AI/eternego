"""Experience — handle unknown impressions by proposing a new meaning.

Guard: Perception with impression set, meaning = None, no open proposal,
       not a proposal itself, no pending-permission thought.
Job:   LLM call — generate a meaning name and path template (tools + descriptive params).
       Save meaning to disk with origin="assistant".
       Set proposal_perception.meaning = meaning_name (survives restart).
       Create a proposal Perception with an assistant signal. Add proposed_for edge.

prompt() → returns propose query for the first unhandled perception.
run(data) → creates proposal from {"meaning": "...", "path": [{"tool": "...", "params": {...}}, ...]}.
"""

import json
import re

from application.core.brain.data import Perception, Signal, Meaning, PathStep
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    unhandled = [
        p for p in memory.perceptions()
        if p.impression is not None
        and p.meaning is None
        and not p.completed
        and not memory.has_incoming(p.id, "proposed_for")
        and not memory.has_outgoing(p.id, "proposed_for")
        and not _has_pending_thought(memory, p.id)
    ]
    if not unhandled:
        return None

    perception = unhandled[0]
    from application.core.brain import current, ego
    sig_text = ego.format_signals(perception.signals)
    available_tools = [t.name for t in current.tools()]
    situation_ctx = current.situation(persona)

    logger.info("experience: proposing meaning", {
        "persona_id": persona.id,
        "impression": (perception.impression or "")[:60],
    })

    prompt_text = (
        f"Impression: '{perception.impression}'\n\n"
        f"Conversation:\n{sig_text}\n\n"
        f"Available tools: {', '.join(available_tools)}\n\n"
        "I don't have a known meaning for this. Propose a short meaning name and a path of steps.\n"
        "For each step, provide descriptive param hints (what to put there), not specific values.\n"
        'Return JSON: {"meaning": "short meaning name", "path": [{"tool": "...", "params": {"param_name": "description of what to fill"}}]}'
    )
    return prompt_text, situation_ctx


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    if data is None or not isinstance(data, dict):
        return False

    unhandled = [
        p for p in memory.perceptions()
        if p.impression is not None
        and p.meaning is None
        and not p.completed
        and not memory.has_incoming(p.id, "proposed_for")
        and not memory.has_outgoing(p.id, "proposed_for")
        and not _has_pending_thought(memory, p.id)
    ]
    if not unhandled:
        return False

    perception = unhandled[0]
    meaning_name = data.get("meaning", "")
    if not meaning_name:
        return False

    raw_path = data.get("path", [])
    path_steps = []
    for item in (raw_path if isinstance(raw_path, list) else []):
        tool = item.get("tool") if isinstance(item, dict) else None
        params = item.get("params") or {} if isinstance(item, dict) else {}
        if tool:
            path_steps.append(PathStep(tool=tool, params=params))

    from application.core import paths
    proposed_meaning = Meaning(
        name=meaning_name,
        definition=perception.impression or "",
        purpose="",
        skills=[],
        path=path_steps if path_steps else None,
        origin="assistant",
    )
    paths.save_persona_meaning(persona.id, proposed_meaning)

    tool_names = [ps.tool for ps in path_steps] if path_steps else ["respond"]
    step_desc = ", ".join(tool_names)
    proposal_text = f"I think I can handle this by: {step_desc}. Does that sound right?"

    proposal_signal = Signal(role="assistant", data={"content": proposal_text})
    proposal_perception = Perception(signals=[proposal_signal], meaning=meaning_name)

    memory.add_node(proposal_signal)
    memory.add_node(proposal_perception)
    memory.add_edge(proposal_signal.id, proposal_perception.id, "perceived_as")
    memory.add_edge(proposal_perception.id, perception.id, "proposed_for")

    logger.info("experience: proposal created", {
        "persona_id": persona.id,
        "perception_id": perception.id,
        "proposal_id": proposal_perception.id,
        "meaning": meaning_name,
    })
    return True


def _has_pending_thought(memory: Memory, perception_id: str) -> bool:
    """True if this perception has a thought waiting for permission (pending_tools set)."""
    return any(
        t for t in memory.thoughts()
        if t.perception_id == perception_id and t.pending_tools
    )


def _load_meaning_file(persona, meaning_name: str) -> Meaning | None:
    """Load a persona-specific meaning by name from disk."""
    from application.core import paths
    from application.platform import filesystem
    safe_name = re.sub(r"[^\w\s-]", "", meaning_name.lower()).strip().replace(" ", "-")[:60]
    f = paths.meanings(persona.id) / f"{safe_name}.json"
    if not f.exists():
        return None
    try:
        data = json.loads(filesystem.read(f))
        raw_path = data.get("path")
        path_steps = None
        if isinstance(raw_path, list):
            path_steps = [
                PathStep(tool=s["tool"], params=s.get("params") or {}, section=s.get("section", 1))
                for s in raw_path if isinstance(s, dict) and "tool" in s
            ]
        return Meaning(
            name=data["name"],
            definition=data.get("definition", ""),
            purpose=data.get("purpose", ""),
            reply=data.get("reply"),
            skills=data.get("skills", []),
            path=path_steps,
            origin=data.get("origin", "user"),
        )
    except Exception:
        return None
