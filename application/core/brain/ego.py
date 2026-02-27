"""Ego — the persona's reasoning engine and cognitive pipeline.

effect(persona)                      builds the character system prompt.
talk(persona, prompt)                converses using the ego system prompt.
reason(persona, prompt)              reasons in JSON mode.
reason(persona, prompt, system)      reasons with an additional system section.

realize(persona, signals)            group signals into threads and title each.
order(persona, perceptions)          order perceptions by priority.
prepare(persona, perception)         select the relevant traits for the top perception.
plan(persona, perception)            produce steps using the perception's selected traits.
"""

from application.core.data import Persona
from application.core.brain import character, current, traits
from application.core.brain.data import Signal, Thread, Meaning, Perception, Step
from application.core import local_model
from application.platform import logger


def effect(persona: Persona) -> str:
    """Build the ego system prompt from character."""
    return character.shape(persona).content


async def talk(persona: Persona, prompt: str) -> str:
    """Call the persona's model conversationally — no structure, no JSON."""
    messages = [
        {"role": "system", "content": effect(persona)},
        {"role": "user", "content": prompt},
    ]
    return await local_model.chat(persona.model.name, messages)


async def reason(persona: Persona, prompt: str, system: str = "") -> dict:
    """Call the persona's model in JSON mode with step-by-step reasoning.

    An optional system string is appended after the base instruction —
    used by cognitive functions to inject task-specific context such as
    the available trait vocabulary.
    """
    def reasoning_system() -> str:
        base = (
            effect(persona)
            + "\n\nReason step by step before responding. "
            "Consider all relevant factors and consequences. "
            "Return your response as a JSON object."
        )
        return base + ("\n\n" + system if system else "")

    messages = [
        {"role": "system", "content": reasoning_system()},
        {"role": "user", "content": prompt},
    ]
    return await local_model.chat_json(persona.model.name, messages)


# ── Cognitive pipeline ────────────────────────────────────────────────────────

async def realize(persona: Persona, signals: list[Signal]) -> list[Perception]:
    """Group signals into related threads and assign a title to each."""
    if not signals:
        return []

    def prompt() -> str:
        lines = [
            "Group the following signals into threads of related signals,",
            "and give each thread a short title (what this thread is about in plain language).",
            'Return JSON: {"perceptions": [{"signals": [0, 1, 2], "title": "..."}]}',
            "Use 0-based signal indices. Every signal must appear in exactly one thread.\n",
        ]
        for i, s in enumerate(signals):
            channel = f" via {s.channel.name}" if s.channel else ""
            lines.append(f"{i}. [{s.prompt.role}{channel}] {s.prompt.content}")
        return "\n".join(lines)

    response = await reason(persona, prompt())
    items = response.get("perceptions") if isinstance(response, dict) else None
    if not isinstance(items, list) or not items:
        logger.warning("ego.realize: model returned unexpected output", {"persona_id": persona.id})
        return []

    used = set()
    result = []
    for item in items:
        indices = item.get("signals", [])
        title = item.get("title", "").strip()
        if not title or not isinstance(indices, list):
            continue
        thread_signals = [signals[i] for i in indices if isinstance(i, int) and 0 <= i < len(signals)]
        if not thread_signals:
            continue
        used.update(i for i in indices if isinstance(i, int) and 0 <= i < len(signals))
        result.append(Perception(Thread(thread_signals), title))

    # Any signal the model missed gets its own thread
    for i, s in enumerate(signals):
        if i not in used:
            result.append(Perception(Thread([s]), s.prompt.content))

    return result


async def order(persona: Persona, perceptions: list[Perception]) -> list[Perception]:
    """Return perceptions ordered from most to least important."""
    if len(perceptions) == 1:
        return perceptions

    def prompt() -> str:
        lines = [
            "Order these perceptions by priority — most important to address first.",
            'Return JSON: {"order": [2, 0, 1]} — 0-based indices in priority order.\n',
        ]
        for i, p in enumerate(perceptions):
            lines.append(f"{i}. {p.title}")
        return "\n".join(lines)

    response = await reason(persona, prompt(), system=current.time())
    indices = response.get("order") if isinstance(response, dict) else None
    if not isinstance(indices, list):
        logger.warning("ego.order: model returned unexpected output", {"persona_id": persona.id})
        return perceptions

    seen = set()
    result = []
    for i in indices:
        if isinstance(i, int) and 0 <= i < len(perceptions) and i not in seen:
            result.append(perceptions[i])
            seen.add(i)

    for i, p in enumerate(perceptions):
        if i not in seen:
            result.append(p)

    return result


async def prepare(persona: Persona, perception: Perception) -> Meaning:
    """Select the relevant traits and skills for this perception and return a Meaning."""
    def prompt() -> str:
        trait_list = current.traits()
        skill_list = current.skills(persona)
        lines = [
            f"Perception: {perception.title}\n",
            "Select only the traits needed to address this perception.",
            'Return JSON: {"traits": ["trait_name", ...], "skills": ["skill_name", ...]}\n',
            "Traits:",
        ]
        for t in trait_list:
            if t.description:
                lines.append(f"- {t.name}: {t.description}")
        if skill_list:
            lines.append("\nSkills (select if you need the how-to knowledge to execute):")
            for s in skill_list:
                if s.description:
                    lines.append(f"- {s.name}: {s.description}")
        return "\n".join(lines)

    response = await reason(persona, prompt())
    if not isinstance(response, dict):
        logger.warning("ego.prepare: model returned unexpected output", {"persona_id": persona.id})
        return Meaning(perception.title)

    selected_traits = response.get("traits") or []
    selected_skills = response.get("skills") or []

    if not isinstance(selected_traits, list):
        logger.warning("ego.prepare: model returned unexpected output", {"persona_id": persona.id})
        return Meaning(perception.title)

    valid_skill_names = {s.name for s in current.skills(persona)}
    valid_traits = [t for t in selected_traits if isinstance(t, str) and traits.for_name(t) is not None]
    valid_skills = [s for s in selected_skills if isinstance(s, str) and s in valid_skill_names]
    return Meaning(perception.title, valid_traits, valid_skills)


async def legalize(persona: Persona, steps: list[Step]) -> list[str]:
    """Check which planned steps require but haven't been granted permission.

    Reads permissions.md and asks the model to identify any traits in the plan
    that declare requires_permission=True and have not been explicitly granted.
    Returns a list of trait names that are blocked.
    """
    from application.core import paths

    # Collect traits in plan that require permission
    guarded = []
    for step in steps:
        t = traits.for_name(step.trait)
        if t and t.requires_permission:
            guarded.append(step.trait)

    if not guarded:
        return []

    permissions_path = paths.permissions(persona.id)
    permissions_content = paths.read(permissions_path)

    def prompt() -> str:
        lines = [
            "The following traits require explicit permission before they can run:",
            ", ".join(guarded),
            "",
            "Permissions file content (lines starting with 'granted:' or 'rejected:'):",
            permissions_content if permissions_content else "(empty — no permissions recorded yet)",
            "",
            "Which of the listed traits are NOT yet granted permission?",
            'Return JSON: {"blocked": ["trait_name", ...]}',
            "Return an empty list if all are granted.",
        ]
        return "\n".join(lines)

    response = await reason(persona, prompt())
    blocked = response.get("blocked") if isinstance(response, dict) else None
    if not isinstance(blocked, list):
        logger.warning("ego.legalize: model returned unexpected output", {"persona_id": persona.id})
        return guarded  # safe default: block all guarded traits if model fails

    return [t for t in blocked if isinstance(t, str)]


async def grant_or_reject(persona: Persona, blocked: list[str], subsequent: list[Signal]) -> dict:
    """Determine if subsequent signals constitute a permission grant or rejection.

    Called only when a person response has arrived after the pending_permission signal.
    Returns {"granted": [...], "rejected": [...]} — empty lists if no clear decision.
    """
    from application.core import paths

    permissions_path = paths.permissions(persona.id)
    permissions_content = paths.read(permissions_path)

    def prompt() -> str:
        signals_text = "\n".join(
            f"[{s.prompt.role}]: {s.prompt.content}" for s in subsequent
        )
        return "\n".join([
            f"These traits are pending permission: {', '.join(blocked)}",
            "",
            "Messages received after the permission request:",
            signals_text,
            "",
            "Current permissions on file:",
            permissions_content if permissions_content else "(none recorded yet)",
            "",
            "Based on the person's response, did they explicitly grant or reject any of these traits?",
            "Only include traits the person clearly authorised or denied.",
            'Return JSON: {"granted": ["trait_name", ...], "rejected": ["trait_name", ...]}',
            "Return empty lists if no clear decision was made.",
        ])

    response = await reason(persona, prompt())
    if not isinstance(response, dict):
        logger.warning("ego.grant_or_reject: unexpected output", {"persona_id": persona.id})
        return {"granted": [], "rejected": []}

    granted = [t for t in (response.get("granted") or []) if isinstance(t, str) and t in blocked]
    rejected = [t for t in (response.get("rejected") or []) if isinstance(t, str) and t in blocked]
    return {"granted": granted, "rejected": rejected}


async def plan(persona: Persona, perception: Perception, meaning: Meaning) -> list[Step]:
    """Plan the steps needed to address a perception using the prepared meaning."""
    def prompt() -> str:
        signals_text = "\n".join(
            f"  [{s.prompt.role}{' via ' + s.channel.name if s.channel else ''}] {s.prompt.content}"
            for s in perception.thread.signals
        )
        return (
            f"Perception: {meaning.title}\n\n"
            f"Signals:\n{signals_text}\n\n"
            "Plan the steps to address this perception using the available traits.\n"
            'Return JSON: {"steps": [{"number": 1, "trait": "trait_name", "params": {}}]}'
        )

    response = await reason(persona, prompt(), system=current.situation(persona, meaning))
    items = response.get("steps") if isinstance(response, dict) else None
    if not isinstance(items, list) or not items:
        logger.warning("ego.plan: model returned unexpected output", {"persona_id": persona.id})
        return []

    result = []
    for item in items:
        number = item.get("number")
        trait_name = item.get("trait")
        params = item.get("params") or {}
        if not isinstance(number, int) or not trait_name:
            continue
        if traits.for_name(trait_name) is None:
            logger.warning("ego.plan: unknown trait in response", {"persona_id": persona.id, "trait": trait_name})
            continue
        result.append(Step(number=number, trait=trait_name, params=params))

    return result
