"""Ego — the persona's reasoning engine and cognitive pipeline.

effect(persona)                                builds the character system prompt.
reason(persona, prompt)                        reasons in JSON mode.
reason(persona, prompt, system)                reasons with an additional system section.
realize(persona, signals)                      group signals into related threads (list[Thread]).
"""

from application.core.data import Persona
from application.core.brain import character, tools
from application.core.brain.data import Signal, Thread, Step
from application.core import local_model
from application.platform import logger


def effect(persona: Persona) -> str:
    """Build the ego system prompt from character."""
    return character.shape(persona).content


async def reason(persona: Persona, prompt: str, system: str = "") -> dict:
    """Call the persona's model in JSON mode with step-by-step reasoning.

    An optional system string is appended after the base instruction —
    used by cognitive functions to inject task-specific context such as
    the available tool vocabulary.
    """
    def reasoning_system() -> str:
        base = (
            effect(persona)
            + "\n\nReason step by step before responding. "
            "Consider all relevant factors and consequences. "
            "Return your response as a JSON object."
        )
        return base + ("\n\n" + system if system else "")

    from application.core import channels
    await channels.express_thinking(persona)
    messages = [
        {"role": "system", "content": reasoning_system()},
        {"role": "user", "content": prompt},
    ]
    return await local_model.chat_json(persona.model.name, messages)


async def realize(persona: Persona, signals: list[Signal]) -> list[Thread]:
    """Group signals into related threads and assign a title to each."""
    logger.info("ego.realize", {"persona_id": persona.id, "signals": len(signals)})
    if not signals:
        return []

    def prompt() -> str:
        lines = [
            "Group the following signals into threads of related signals,",
            "and give each thread a short title (what this thread is about in plain language).",
            'Return JSON: {"threads": [{"signals": [0, 1, 2], "title": "..."}]}',
            "Use 0-based signal indices. Every signal must appear in exactly one thread.\n",
        ]
        for i, s in enumerate(signals):
            channel = f" via {s.channel.name}" if s.channel else ""
            time = s.created_at.strftime("%H:%M")
            lines.append(f"{i}. [{s.id}] [{s.prompt.role}{channel} at {time}] {s.prompt.content}")
        return "\n".join(lines)

    response = await reason(persona, prompt())
    items = response.get("threads") if isinstance(response, dict) else None
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
        result.append(Thread(signals=thread_signals, title=title))

    # Any signal the model missed gets its own thread
    for i, s in enumerate(signals):
        if i not in used:
            result.append(Thread(signals=[s], title=s.prompt.content))

    return result


async def legalize(persona: Persona, steps: list[Step]) -> list[str]:
    """Check which planned steps require but haven't been granted permission.


    Reads permissions.md and asks the model to identify any tools in the plan
    that declare requires_permission=True and have not been explicitly granted.
    Returns a list of tool names that are blocked.
    """
    logger.info("ego.legalize", {"persona_id": persona.id, "steps": len(steps)})
    from application.core import paths

    # Collect tools in plan that require permission
    guarded = []
    for step in steps:
        t = tools.for_name(step.tool)
        if t and t.requires_permission:
            guarded.append(step.tool)

    if not guarded:
        return []

    permissions_path = paths.permissions(persona.id)
    permissions_content = paths.read(permissions_path)

    def prompt() -> str:
        lines = [
            "The following tools require explicit permission before they can run:",
            ", ".join(guarded),
            "",
            "Permissions file content (lines starting with 'granted:' or 'rejected:'):",
            permissions_content if permissions_content else "(empty — no permissions recorded yet)",
            "",
            "Which of the listed tools are NOT yet granted permission?",
            'Return JSON: {"blocked": ["tool_name", ...]}',
            "Return an empty list if all are granted.",
        ]
        return "\n".join(lines)

    response = await reason(persona, prompt())
    blocked = response.get("blocked") if isinstance(response, dict) else None
    if not isinstance(blocked, list):
        logger.warning("ego.legalize: model returned unexpected output", {"persona_id": persona.id})
        return guarded  # safe default: block all guarded tools if model fails

    return [t for t in blocked if isinstance(t, str)]


async def grant_or_reject(persona: Persona, blocked: list[str], subsequent: list[Signal]) -> dict:
    """Determine if subsequent signals constitute a permission grant or rejection.

    Called only when a person response has arrived after the pending_permission signal.
    Returns {"granted": [...], "rejected": [...]} — empty lists if no clear decision.
    """
    logger.info("ego.grant_or_reject", {"persona_id": persona.id, "blocked": blocked})
    from application.core import paths

    permissions_path = paths.permissions(persona.id)
    permissions_content = paths.read(permissions_path)

    def prompt() -> str:
        signals_text = "\n".join(
            f"[{s.prompt.role}]: {s.prompt.content}" for s in subsequent
        )
        return "\n".join([
            f"These tools are pending permission: {', '.join(blocked)}",
            "",
            "Messages received after the permission request:",
            signals_text,
            "",
            "Current permissions on file:",
            permissions_content if permissions_content else "(none recorded yet)",
            "",
            "Based on the person's response, did they explicitly grant or reject any of these tools?",
            "Only include tools the person clearly authorised or denied.",
            'Return JSON: {"granted": ["tool_name", ...], "rejected": ["tool_name", ...]}',
            "Return empty lists if no clear decision was made.",
        ])

    response = await reason(persona, prompt())
    if not isinstance(response, dict):
        logger.warning("ego.grant_or_reject: unexpected output", {"persona_id": persona.id})
        return {"granted": [], "rejected": []}

    granted = [t for t in (response.get("granted") or []) if isinstance(t, str) and t in blocked]
    rejected = [t for t in (response.get("rejected") or []) if isinstance(t, str) and t in blocked]
    return {"granted": granted, "rejected": rejected}


async def recap(persona: Persona, signals: list["Signal"], results: str, interrupted_by: "Signal | None" = None) -> str:
    """Produce a one-sentence narrative of what just happened. Used during sleep consolidation."""
    logger.info("ego.recap", {"persona_id": persona.id, "signals": len(signals)})
    def prompt() -> str:
        signals_text = "\n".join(f"[{s.prompt.role}]: {s.prompt.content}" for s in signals)
        results_part = f"\n\nExecution results:\n{results.strip()}" if results.strip() else ""
        interruption_part = (
            f"\n\nInterrupted by: {interrupted_by.prompt.content}" if interrupted_by else ""
        )
        return (
            f"Signals:\n{signals_text}{results_part}{interruption_part}\n\n"
            "Write one sentence summarising what happened. "
            "Example: 'Person asked for the weather and Persona answered using web tools.'\n"
            'Return JSON: {"recap": "..."}'
        )

    response = await reason(persona, prompt())
    return response.get("recap", "") if isinstance(response, dict) else ""


