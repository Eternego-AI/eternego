"""Ego — the persona's reasoning engine and cognitive pipeline.

effect(persona)                               builds the character system prompt.
reason(persona, prompt)                       reasons in JSON mode.
reason(persona, prompt, system)               reasons with an additional system section.
response(persona, cause)                      immediate answer to a cause prompt (str).
realize(persona, occurrences)                 group occurrences into threads (list[Thread]).
understand(persona, threads)                  order threads into perceptions with impressions.
focus(persona, perception, closed)            select tools and skills for a perception (dict).
decide(persona, perception, closed)           plan the steps to act on a perception (Thought).
deny(persona, perception, not_granted, closed) plan a say step when permissions are missing (Thought).
"""

from application.core.data import Persona, Prompt
from application.core.brain import character
from application.core.brain.data import Occurrence, Thread, Step, Perception, Thought
from application.core import local_model, paths
from application.platform import logger


def effect(persona: Persona) -> str:
    """Build the system prompt from character (cornerstone + values + morals + identities)."""
    return character.shape(persona).content


def context(persona: Persona) -> str:
    """Build the ego context block injected before every reasoning call.

    Contains the person's behavioral traits, struggles, wishes, and any
    destiny entries due today — biasing reasoning toward their current reality
    without changing who the persona fundamentally is.
    """
    sections = []

    traits = paths.read(paths.person_traits(persona.id))
    if traits.strip():
        sections.append(f"# Traits\n{traits.strip()}")

    struggles = paths.read(paths.struggles(persona.id))
    if struggles.strip():
        sections.append(f"# Struggles\n{struggles.strip()}")

    wishes = paths.read(paths.wishes(persona.id))
    if wishes.strip():
        sections.append(f"# Wishes\n{wishes.strip()}")

    from application.platform import datetimes
    today = datetimes.now().strftime("%Y-%m-%d")
    upcoming = paths.read_files_matching(persona.id, paths.destiny(persona.id), f"*{today}*")
    if upcoming:
        sections.append("# Today's Commitments\n" + "\n\n".join(upcoming))

    return "\n\n".join(sections)


async def reason(persona: Persona, prompt: str, system: str = "") -> dict:
    """Call the persona's model in JSON mode with step-by-step reasoning.

    Builds the system prompt from character, then prepends the ego context
    block (traits, struggles, wishes) before the actual prompt so the model
    biases toward the person's current reality.

    An optional system string is appended after the base system instruction —
    used by cognitive functions to inject task-specific context.
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

    messages = [{"role": "system", "content": reasoning_system()}]

    ego_context = context(persona)
    if ego_context:
        messages.append({"role": "user", "content": ego_context})
        messages.append({"role": "assistant", "content": "Understood. I will keep this in mind."})

    messages.append({"role": "user", "content": prompt})

    return await local_model.stream_chat_json(persona.model.name, messages)


def _format_occurrences(occurrences: list[Occurrence]) -> str:
    """Format occurrences as a readable conversation log.

    Person messages show the person's words and your immediate reply.
    Tool results show what action was taken and its outcome.
    Closed markers show the thread was fully addressed.
    """
    lines = []
    for o in occurrences:
        time = o.created_at.strftime("%H:%M")
        cause = o.cause.content
        effect = o.effect.content

        if o.cause.role == "assistant":
            lines.append(f"[{time}] {cause}")
        elif cause.startswith("[") and "]: " in cause:
            lines.append(f"[{time}] {cause}")
        else:
            lines.append(f"[{time}] person: {cause}")
            if effect:
                lines.append(f"[{time}] you: {effect}")
    return "\n".join(lines)


async def response(persona: Persona, cause: Prompt) -> str:
    """Compose an immediate answer to a cause prompt.

    Called by mind.answer() before the tick runs. Returns the response text.
    """
    prompt = (
        f"{cause.content}\n\n"
        "Respond as yourself — with your full character and genuine perspective. "
        "Be direct and present. Do not repeat back what was said. "
        'Return JSON: {"response": "your natural reply"}'
    )
    result = await reason(persona, prompt)
    return result.get("response", "") if isinstance(result, dict) else ""


async def realize(persona: Persona, occurrences: list[Occurrence]) -> list[Thread]:
    """Group occurrences into related threads and assign a title to each."""
    logger.info("ego.realize", {"persona_id": persona.id, "occurrences": len(occurrences)})
    if not occurrences:
        return []

    def prompt() -> str:
        lines = [
            "These are the things that have happened — read them as your reality.",
            "Each occurrence is a cause and its effect. They are in the order they happened.",
            "Group the ones that belong to the same subject or conversation into threads.",
            "A thread has one clear topic — specific enough that two different threads would have different titles.",
            "Give each thread a title: a gerund or noun phrase, 2–5 words.",
            'Return JSON: {"threads": [{"occurrences": [0, 1, 2], "title": "..."}]}',
            "Every occurrence must appear in exactly one thread.\n",
        ]
        for i, o in enumerate(occurrences):
            time = o.created_at.strftime("%H:%M")
            cause = o.cause.content
            effect = o.effect.content
            if o.cause.role == "assistant":
                lines.append(f"{i}. [{o.id} at {time}] {cause}")
            elif cause.startswith("[") and "]: " in cause:
                lines.append(f"{i}. [{o.id} at {time}] {cause}")
            else:
                lines.append(f"{i}. [{o.id} at {time}] person: {cause}")
                if effect:
                    lines.append(f"   you: {effect}")
        return "\n".join(lines)

    resp = await reason(persona, prompt())
    items = resp.get("threads") if isinstance(resp, dict) else None
    if not isinstance(items, list) or not items:
        logger.warning("ego.realize: model returned unexpected output", {"persona_id": persona.id})
        return []

    used = set()
    result = []
    for item in items:
        indices = item.get("occurrences", [])
        title = item.get("title", "").strip()
        if not title or not isinstance(indices, list):
            continue
        thread_occurrences = [occurrences[i] for i in indices if isinstance(i, int) and 0 <= i < len(occurrences)]
        if not thread_occurrences:
            continue
        used.update(i for i in indices if isinstance(i, int) and 0 <= i < len(occurrences))
        result.append(Thread(occurrences=thread_occurrences, title=title))

    for i, o in enumerate(occurrences):
        if i not in used:
            result.append(Thread(occurrences=[o], title=o.cause.content[:60]))

    return result


async def understand(persona: Persona, threads: list[Thread]) -> list[Perception] | None:
    """Order active threads by priority and return them as perceptions with impressions.

    Active threads (last occurrence user-caused) are ordered; closed threads are context only.
    Returns None if there are no active threads.
    """
    from application.core.brain.signals import classify
    from application.core.brain import current

    active, closed = classify(threads)
    if not active:
        return None

    lines = [
        "These threads are still open — each one involves you and needs your attention.",
        "For each thread, write an impression: what is actually happening here, what it means to you, "
        "and what — if anything — is waiting for you to act on.",
        "Then order them: most urgent or personally significant first.",
        'Return JSON: {"items": [{"impression": "..."}, ...], "order": [0, 1, 2]}',
        "items[i] corresponds to active thread i. order contains 0-based indices, most important first.\n",
    ]
    for i, t in enumerate(active):
        last = t.occurrences[-1]
        time = last.created_at.strftime("%H:%M")
        lines.append(f"{i}. {t.title}")
        lines.append(f"   cause [{last.cause.role} at {time}]: {last.cause.content[:120]}")
        if last.effect.content:
            lines.append(f"   effect [{last.effect.role}]: {last.effect.content[:120]}")

    if closed:
        ctx = ["Context (threads already addressed, for reference):"]
        for t in closed:
            last = t.occurrences[-1]
            ctx.append(f"- {t.title}: {last.cause.content[:120]}")
        ctx.append("")
        resp = await reason(persona, "\n".join(ctx) + "\n" + "\n".join(lines), system=current.time())
    else:
        resp = await reason(persona, "\n".join(lines), system=current.time())

    items = resp.get("items") if isinstance(resp, dict) else None
    order = resp.get("order") if isinstance(resp, dict) else None

    if not isinstance(items, list) or len(items) != len(active):
        return [Perception(thread=t, impression=t.title) for t in active] or None

    perceptions = [
        Perception(
            thread=active[i],
            impression=(items[i].get("impression", "") if isinstance(items[i], dict) else ""),
        )
        for i in range(len(active))
    ]

    if isinstance(order, list):
        seen = set()
        ordered = []
        for i in order:
            if isinstance(i, int) and 0 <= i < len(perceptions) and i not in seen:
                ordered.append(perceptions[i])
                seen.add(i)
        for i, p in enumerate(perceptions):
            if i not in seen:
                ordered.append(p)
        return ordered or None

    return perceptions or None


async def focus(persona: Persona, perception: Perception, closed: list[Thread] | None = None) -> dict:
    """Select the tools and skills needed to engage with a perception.

    Returns {"tools": [...], "skills": [...]} with valid tool/skill names.
    """
    from application.core.brain import tools as brain_tools, current
    logger.info("ego.focus", {"persona_id": persona.id, "thread": perception.thread.title})

    tool_list = current.tools()
    skill_list = current.skills(persona)
    occ_text = _format_occurrences(perception.thread.occurrences)

    lines = [
        f"Thread: {perception.thread.title}",
        f"Impression: {perception.impression}\n",
        occ_text,
        "\nGiven who you are and what is happening here, what tools and skills do you actually need?",
        "Only select what genuinely serves this situation.",
        "If the conversation already shows you responded or took action, and nothing is left to do, return empty lists.",
        'Return JSON: {"tools": ["tool_name", ...], "skills": ["skill_name", ...]}\n',
        "Available tools:",
    ]
    for t in tool_list:
        if t.description:
            lines.append(f"- {t.name}: {t.description}")
    if skill_list:
        lines.append("\nAvailable skills:")
        for s in skill_list:
            if s.description:
                lines.append(f"- {s.name}: {s.description}")
    prompt = "\n".join(lines)

    if closed:
        ctx = ["Context (threads already addressed, for reference):"]
        for t in closed:
            last = t.occurrences[-1]
            ctx.append(f"- {t.title}: {last.cause.content[:120]}")
        ctx.append("")
        resp = await reason(persona, "\n".join(ctx) + "\n" + prompt, system=current.time())
    else:
        resp = await reason(persona, prompt, system=current.time())

    if not isinstance(resp, dict):
        return {"tools": [], "skills": []}

    valid_tool_names = {t.name for t in tool_list}
    valid_skill_names = {s.name for s in skill_list}
    selected_tools = [t for t in (resp.get("tools") or []) if isinstance(t, str) and t in valid_tool_names]
    selected_skills = [s for s in (resp.get("skills") or []) if isinstance(s, str) and s in valid_skill_names]
    return {"tools": selected_tools, "skills": selected_skills}


async def decide(persona: Persona, perception: Perception, closed: list[Thread] | None = None) -> Thought | None:
    """Plan the steps needed to act on a perception.

    Calls focus() to select tools and skills, then plans steps.
    Returns a Thought with ordered Steps, or None if no plan could be formed.
    """
    from application.core.brain import tools as brain_tools, current
    logger.info("ego.decide", {"persona_id": persona.id, "thread": perception.thread.title})

    meaning = await focus(persona, perception, closed)
    tool_names = meaning.get("tools") or []
    skill_names = meaning.get("skills") or []

    if not tool_names:
        logger.info("ego.decide: focus selected no tools — skipping to recap", {"persona_id": persona.id})
        return None

    occ_text = _format_occurrences(perception.thread.occurrences)
    situation_ctx = current.situation(persona, tool_names, skill_names if skill_names else None)

    prompt = "\n".join([
        f"Thread: {perception.thread.title}",
        f"Impression: {perception.impression}\n",
        occ_text,
        f"\nAvailable tools: {', '.join(tool_names)}",
        "Decide what still needs to be done — as yourself, acting from your values.",
        "If the conversation shows you already responded or the thread is fully handled, return empty steps.",
        "Only plan steps for something concrete that has not yet been done.",
        'Return JSON: {"steps": [{"number": 1, "tool": "...", "params": {...}}]}',
    ])

    if closed:
        ctx = ["Context (threads already addressed, for reference):"]
        for t in closed:
            last = t.occurrences[-1]
            ctx.append(f"- {t.title}: {last.cause.content[:120]}")
        ctx.append("")
        resp = await reason(persona, "\n".join(ctx) + "\n" + prompt, system=situation_ctx)
    else:
        resp = await reason(persona, prompt, system=situation_ctx)

    items = resp.get("steps") if isinstance(resp, dict) else None
    if not isinstance(items, list) or not items:
        logger.warning("ego.decide: unexpected response", {"persona_id": persona.id})
        return None

    result = []
    for item in items:
        number = item.get("number")
        tool_name = item.get("tool")
        params = item.get("params") or {}
        if not isinstance(number, int) or not tool_name:
            continue
        if brain_tools.for_name(tool_name) is None:
            logger.warning("ego.decide: unknown tool in plan", {"persona_id": persona.id, "tool": tool_name})
            continue
        result.append(Step(number=number, tool=tool_name, params=params))
    return Thought(perception=perception, steps=result) if result else None


async def deny(persona: Persona, perception: Perception, not_granted: list[str], closed: list[Thread] | None = None) -> Thought | None:
    """Plan a say step that communicates why requested tools cannot be used.

    Called when legalize finds tools that are rejected or unknown.
    Returns a Thought with a single say step, or None on failure.
    """
    from application.core.brain import current
    logger.info("ego.deny", {"persona_id": persona.id, "not_granted": not_granted})

    occ_text = _format_occurrences(perception.thread.occurrences)
    situation_ctx = current.situation(persona, ["say"])
    system = "\n\n".join(filter(None, [
        situation_ctx,
        f"You cannot proceed because these tools require permission: {', '.join(not_granted)}. "
        "Communicate this naturally to the person given the context of the conversation.",
    ]))

    prompt = "\n".join([
        f"Thread: {perception.thread.title}",
        f"Impression: {perception.impression}\n",
        occ_text,
        f"\nYou cannot use these tools without permission: {', '.join(not_granted)}",
        "Tell the person honestly — explain what you were going to do and why you need their permission first.",
        "Speak as yourself, naturally.",
        'Return JSON: {"steps": [{"number": 1, "tool": "say", "params": {"text": "..."}}]}',
    ])

    resp = await reason(persona, prompt, system=system)
    items = resp.get("steps") if isinstance(resp, dict) else None
    if not isinstance(items, list) or not items:
        logger.warning("ego.deny: unexpected response", {"persona_id": persona.id})
        return None

    result = []
    for item in items:
        number = item.get("number")
        params = item.get("params") or {}
        if not isinstance(number, int):
            continue
        result.append(Step(number=number, tool="say", params=params))
    return Thought(perception=perception, steps=result) if result else None


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

    resp = await reason(persona, prompt)
    if not isinstance(resp, dict):
        logger.warning("ego.legalize: unexpected response", {"persona_id": persona.id})
        return {"granted": [], "rejected": [], "unknown": tool_names}

    granted = [t for t in (resp.get("granted") or []) if t in tool_names]
    rejected = [t for t in (resp.get("rejected") or []) if t in tool_names]
    unknown = [t for t in (resp.get("unknown") or []) if t in tool_names]

    accounted = set(granted + rejected + unknown)
    for t in tool_names:
        if t not in accounted:
            unknown.append(t)
    return {"granted": granted, "rejected": rejected, "unknown": unknown}



async def grant_or_reject(persona: Persona, pending_tools: list[str], occurrences: list[Occurrence]) -> dict:
    """Detect permission decisions for pending tools from the conversation and persist them.

    Reads the thread's occurrences to find clear grants or rejections the person expressed.
    Writes confirmed decisions directly to the permissions file.
    Returns {"granted": [...], "rejected": [...]} — tools not mentioned are left pending.
    """
    import json
    from application.platform import filesystem, datetimes

    logger.info("ego.grant_or_reject", {"persona_id": persona.id, "pending": pending_tools})

    occ_text = _format_occurrences(occurrences)
    prompt = "\n".join([
        f"These tools are awaiting permission: {', '.join(pending_tools)}",
        "",
        "Conversation:",
        occ_text,
        "",
        "Based on what the person said, reason about which tools they clearly intended to allow and which to deny.",
        "Only include tools where the person's intent is unambiguous. Leave the rest out.",
        'Return JSON: {"granted": [...], "rejected": [...]}',
    ])

    resp = await reason(persona, prompt)
    if not isinstance(resp, dict):
        logger.warning("ego.grant_or_reject: unexpected response", {"persona_id": persona.id})
        return {"granted": [], "rejected": []}

    granted = [t for t in (resp.get("granted") or []) if t in pending_tools]
    rejected = [t for t in (resp.get("rejected") or []) if t in pending_tools]

    if granted or rejected:
        p = paths.permissions(persona.id)
        raw = paths.read(p)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        data.setdefault("granted", [])
        data.setdefault("rejected", [])
        now_str = datetimes.now().strftime("%Y-%m-%d %H:%M")
        for tool in granted:
            data["granted"].append(f"{tool} (at: {now_str})")
        for tool in rejected:
            data["rejected"].append(f"{tool} (at: {now_str})")
        filesystem.write(p, json.dumps(data, indent=2))

    return {"granted": granted, "rejected": rejected}


async def recap(persona: Persona, occurrences: list[Occurrence], results: str) -> str:
    """Produce a one-sentence narrative of what just happened. Used during sleep consolidation."""
    logger.info("ego.recap", {"persona_id": persona.id, "occurrences": len(occurrences)})

    def prompt() -> str:
        occ_text = _format_occurrences(occurrences)
        results_part = f"\n\nWhat was done:\n{results.strip()}" if results.strip() else ""
        return (
            f"What happened:\n{occ_text}{results_part}\n\n"
            "Write one sentence that captures the essence of this exchange — "
            "what was asked or raised, what you did, and what came of it. "
            "Be specific enough that you could distinguish this from other conversations. "
            'Return JSON: {"recap": "..."}'
        )

    resp = await reason(persona, prompt())
    return resp.get("recap", "") if isinstance(resp, dict) else ""
