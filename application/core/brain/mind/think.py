"""Think — plan a Thought for the next section of a perception's meaning path.

Guard: Perception with impression and meaning set, not completed,
       and no existing Thought planned for it.
Job:   Derive the current section by counting successful result signals already
       in perception.signals.
       If no user-fillable slots in current section → build Thought directly (no LLM).
       If all sections are done → add information{type: "end"} signal and mark completed.

Special param values:
  "$perception_id" — injected here with the perception's id before execution.
  "$tool_output"   — passed through; injected at execution time by do.py.

prompt() → returns decide query or None (no LLM needed / guard not met).
run(data) → creates Thought from plan result, or builds it directly if no slots.
"""

import json

from application.core.brain.data import Signal, Thought, Step
from application.core.brain.mind.memory import Memory
from application.core import paths as core_paths
from application.core.data import Persona
from application.platform import logger, datetimes


_SYSTEM_INJECTED = ("$perception_id", "$tool_output")


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    perception = _find_pending(memory)
    if perception is None:
        return None

    meaning = _load_meaning(persona, perception.meaning)
    if meaning is None:
        logger.warning("think: meaning not found", {
            "persona_id": persona.id,
            "meaning": perception.meaning,
        })
        return None

    if meaning.path is None:
        return None

    current_section = _current_section(perception, meaning)
    if current_section is None:
        return None  # all done; run() will produce end signal

    section_steps = [ps for ps in meaning.path if ps.section == current_section]

    from application.core.brain import ego, current
    sig_text = ego.format_signals(perception.signals)

    slot_steps = [
        {"tool": ps.tool, "fill": {k: v for k, v in ps.params.items() if v not in _SYSTEM_INJECTED}}
        for ps in section_steps
        if any(v not in _SYSTEM_INJECTED for v in ps.params.values())
    ]
    if not slot_steps:
        return None  # no user-fillable slots; run() builds the Thought directly

    tool_names = [ps.tool for ps in section_steps]
    situation_ctx = current.situation(persona, tool_names, meaning.skills if meaning.skills else None)

    prompt_lines = [f"Impression: {perception.impression}"]
    if meaning.purpose:
        prompt_lines.append(f"Purpose: {meaning.purpose}")
    prompt_lines += [
        "",
        sig_text,
        "",
        "Fill in the parameters for each step. Return JSON:",
        '{"filled": [{"tool": "tool_name", "params": {...}}, ...]}',
        "",
        "Steps to fill:",
        json.dumps(slot_steps, indent=2),
    ]

    logger.info("think: planning", {
        "persona_id": persona.id,
        "impression": (perception.impression or "")[:60],
        "section": current_section,
    })
    return "\n".join(prompt_lines), situation_ctx


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    perception = _find_pending(memory)
    if perception is None:
        return False

    meaning = _load_meaning(persona, perception.meaning)
    if meaning is None:
        return False

    if meaning.path is None:
        # No path — mark completed (recognize should have done this, but safeguard)
        perception.completed = True
        logger.warning("think: meaning has no path, marking completed", {
            "persona_id": persona.id,
            "perception_id": perception.id,
        })
        return True

    current_section = _current_section(perception, meaning)
    if current_section is None:
        # All sections done — produce end signal and mark completed
        end_signal = Signal(role="information", data={"type": "end"})
        memory.add_node(end_signal)
        perception.signals.append(end_signal)
        memory.add_edge(end_signal.id, perception.id, "perceived_as")
        perception.completed = True
        logger.info("think: all sections done", {
            "persona_id": persona.id,
            "perception_id": perception.id,
        })
        return True

    section_steps = [ps for ps in meaning.path if ps.section == current_section]

    if data is None:
        # No user-fillable slots — build Thought directly
        if not _has_user_slots(section_steps):
            steps = [
                Step(
                    number=i + 1,
                    tool=ps.tool,
                    params={
                        k: (perception.id if v == "$perception_id" else v)
                        for k, v in ps.params.items()
                    },
                )
                for i, ps in enumerate(section_steps)
            ]
            thought = Thought(
                perception_id=perception.id,
                steps=steps,
            )
            memory.add_node(thought)
            memory.add_edge(thought.id, perception.id, "planned_for")
            logger.info("think: thought planned (no-slot)", {
                "persona_id": persona.id,
                "perception_id": perception.id,
                "thought_id": thought.id,
                "section": current_section,
            })
            return True
        return False

    thought = _apply_path_result(data, perception, section_steps)

    if thought is None:
        perception.completed = True
        return True

    memory.add_node(thought)
    memory.add_edge(thought.id, perception.id, "planned_for")
    logger.info("think: thought planned", {
        "persona_id": persona.id,
        "perception_id": perception.id,
        "thought_id": thought.id,
        "section": current_section,
        "steps": len(thought.steps),
    })
    return True


def _current_section(perception, meaning) -> int | None:
    """Derive the current section from successful result signals already in perception.

    Returns the section number to plan next, or None if all sections are done.
    """
    all_sections = sorted({ps.section for ps in meaning.path})
    completed_steps = sum(
        1 for s in perception.signals
        if s.role == "result" and s.data.get("success", False)
    )
    accumulated = 0
    for section_num in all_sections:
        section_step_count = sum(1 for ps in meaning.path if ps.section == section_num)
        if accumulated + section_step_count > completed_steps:
            return section_num
        accumulated += section_step_count
    return None  # all sections done


def _apply_path_result(data: dict, perception, section_steps) -> Thought | None:
    filled_items = data.get("filled", []) if isinstance(data, dict) else []
    if not isinstance(filled_items, list):
        filled_items = []

    filled_map: dict[str, dict] = {}
    for item in filled_items:
        if isinstance(item, dict) and "tool" in item:
            filled_map[item["tool"]] = item.get("params") or {}

    steps = []
    for i, path_step in enumerate(section_steps):
        params = {}
        for k, v in path_step.params.items():
            if v == "$perception_id":
                params[k] = perception.id
            elif v == "$tool_output":
                params[k] = "$tool_output"  # resolved at execution time by do.py
            else:
                params[k] = filled_map.get(path_step.tool, {}).get(k, v)
        steps.append(Step(number=i + 1, tool=path_step.tool, params=params))

    return Thought(
        perception_id=perception.id,
        steps=steps,
    ) if steps else None


def _has_user_slots(section_steps) -> bool:
    """True if section steps have any params that are not system-injected."""
    return any(
        v not in _SYSTEM_INJECTED
        for ps in section_steps
        for v in ps.params.values()
    )


def _find_pending(memory: Memory):
    for p in memory.perceptions():
        if not p.impression or not p.meaning or p.completed:
            continue
        if memory.has_outgoing(p.id, "proposed_for"):
            continue
        if not any(t for t in memory.thoughts() if t.perception_id == p.id):
            return p
    return None


def _load_meaning(persona, meaning_name: str):
    from application.core.brain import ego, meanings as brain_meanings

    for m in brain_meanings.all_meanings():
        if m.name == meaning_name:
            return m

    for m in ego.load_persona_meanings(persona):
        if m.name == meaning_name:
            return m

    return None
