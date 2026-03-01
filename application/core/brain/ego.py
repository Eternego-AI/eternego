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


async def legalize(persona: Persona, steps: list[Step]) -> dict:
    """Check permissions for planned steps against the persistent permissions file.

    Returns {"granted": [...], "rejected": [...], "unknown": [...]} —
    every tool name in exactly one list. The model reasons from the
    permissions file content; no code-level requires_permission filtering.
    """
    logger.info("ego.legalize", {"persona_id": persona.id, "steps": len(steps)})
    import json
    from application.core import paths

    tool_names = [s.tool for s in steps]
    if not tool_names:
        return {"granted": [], "rejected": [], "unknown": []}

    raw = paths.read(paths.permissions(persona.id))
    try:
        permissions_data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        permissions_data = {}
    permissions_text = json.dumps(permissions_data, indent=2) if permissions_data else "(none — no permissions recorded yet)"

    prompt = "\n".join([
        f"We are about to run: {', '.join(tool_names)}",
        "",
        "Permissions on file:",
        permissions_text,
        "",
        "Based on what the person has permitted or denied, decide for each tool whether it is covered (granted), ruled out (rejected), or not addressed (unknown).",
        'Return JSON: {"granted": [...], "rejected": [...], "unknown": [...]}',
        "Every tool name must appear in exactly one list.",
    ])

    response = await reason(persona, prompt)
    if not isinstance(response, dict):
        logger.warning("ego.legalize: unexpected response", {"persona_id": persona.id})
        return {"granted": [], "rejected": [], "unknown": tool_names}

    granted = [t for t in (response.get("granted") or []) if t in tool_names]
    rejected = [t for t in (response.get("rejected") or []) if t in tool_names]
    unknown = [t for t in (response.get("unknown") or []) if t in tool_names]

    accounted = set(granted + rejected + unknown)
    for t in tool_names:
        if t not in accounted:
            unknown.append(t)
    return {"granted": granted, "rejected": rejected, "unknown": unknown}


async def grant_or_reject(persona: Persona, pending_tools: list[str], thread_signals: list[Signal]) -> dict:
    """Detect grants/rejections for pending tools from the focused thread's conversation.

    Returns {"granted": [...], "rejected": [...]} — tools not mentioned are left pending.
    """
    logger.info("ego.grant_or_reject", {"persona_id": persona.id, "pending": pending_tools})

    signals_text = "\n".join(
        f"[{s.prompt.role} at {s.created_at.strftime('%H:%M')}]: {s.prompt.content}"
        for s in thread_signals
    )
    prompt = "\n".join([
        f"These tools are awaiting permission: {', '.join(pending_tools)}",
        "",
        "Conversation:",
        signals_text,
        "",
        "Based on what the person said, reason about which tools they intended to allow and which they intended to deny.",
        "Only include tools where the person's intent is clear. Leave the rest out.",
        'Return JSON: {"granted": [...], "rejected": [...]}',
    ])

    response = await reason(persona, prompt)
    if not isinstance(response, dict):
        logger.warning("ego.grant_or_reject: unexpected response", {"persona_id": persona.id})
        return {"granted": [], "rejected": []}

    granted = [t for t in (response.get("granted") or []) if t in pending_tools]
    rejected = [t for t in (response.get("rejected") or []) if t in pending_tools]
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


