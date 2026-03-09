"""Ego — the persona's reasoning engine.

effect(persona)                  builds the character system prompt.
reason(persona, prompt, system)  reasons in JSON mode; the single LLM primitive.
format_signals(signals)          formats a signal list as a readable log.
to_message(signal)               converts a Signal to an LLM message dict.
load_persona_meanings(persona)   loads persona-specific meanings from disk.

Permission functions (called by legalize module):
  legalize(persona, steps)                     permissions check for planned steps.
  deny(persona, perception, not_granted)       generate denial text when permissions missing.
  grant_or_reject(persona, pending, signals)   detect permission decisions from signals.
"""

import json

from application.core.data import Persona, Prompt
from application.core.brain import character
from application.core.brain.data import Signal, Perception, Step, Thought, Meaning
from application.core import local_model, paths
from application.platform import logger, filesystem


def effect(persona: Persona) -> str:
    """Build the system prompt from character (cornerstone + values + morals + identities)."""
    return character.shape(persona).content


async def reason(persona: Persona, prompt: str, system: str = "") -> dict:
    """Call the persona's model in JSON mode. Returns a parsed JSON dict."""
    def reasoning_system() -> str:
        base = effect(persona) + "\n\nReturn your response as a JSON object."
        return base + ("\n\n" + system if system else "")

    from application.core import channels
    await channels.express_thinking(persona)

    messages = [
        {"role": "system", "content": reasoning_system()},
        {"role": "user", "content": prompt},
    ]

    return await local_model.stream_chat_json(persona.model.name, messages)


def format_signals(signals: list[Signal]) -> str:
    """Format signals as a readable conversation log."""
    lines = []
    for s in signals:
        time = s.created_at.strftime("%H:%M")
        if s.role == "user":
            content = s.data.get("content", "")
            lines.append(f"[{time}] person: {content}")
        elif s.role == "assistant":
            content = s.data.get("content", "")
            lines.append(f"[{time}] {content}")
        elif s.role == "result":
            tool = s.data.get("tool", "?")
            output = s.data.get("output", "")
            lines.append(f"[{time}] [{tool}]: {output}")
        # plan and information signals are not shown in conversation display
    return "\n".join(lines)


def to_message(signal: Signal) -> dict | None:
    """Convert a Signal to an LLM message dict, or None if not applicable."""
    if signal.role == "user":
        return {"role": "user", "content": signal.data.get("content", "")}
    if signal.role == "assistant":
        return {"role": "assistant", "content": signal.data.get("content", "")}
    if signal.role == "result":
        return {"role": "user", "content": f"[{signal.data.get('tool')}]: {signal.data.get('output', '')}"}
    return None  # plan and information signals are not sent to LLM


def load_persona_meanings(persona: Persona) -> list[Meaning]:
    """Load persona-specific meanings from JSON files in persona/meanings/."""
    meanings_dir = paths.meanings(persona.id)
    if not meanings_dir.exists():
        return []

    from application.core.brain.data import PathStep

    result = []
    for f in sorted(meanings_dir.glob("*.json")):
        try:
            content = filesystem.read(f)
            if not content:
                continue
            data = json.loads(content.strip())
            if not (isinstance(data, dict) and "name" in data):
                continue
            raw_path = data.get("path")
            path_steps = None
            if isinstance(raw_path, list):
                path_steps = [
                    PathStep(
                        tool=s["tool"],
                        params=s.get("params") or {},
                        section=s.get("section", 1),
                    )
                    for s in raw_path if isinstance(s, dict) and "tool" in s
                ]
            result.append(Meaning(
                name=data["name"],
                definition=data.get("definition", ""),
                purpose=data.get("purpose", ""),
                reply=data.get("reply"),
                skills=data.get("skills", []),
                path=path_steps,
                origin=data.get("origin", "user"),
            ))
        except Exception as e:
            logger.warning("ego.load_persona_meanings: skipping", {
                "file": f.name, "error": str(e)
            })
    return result


# Keep old name as alias for backwards compatibility with any callers
_load_persona_meanings = load_persona_meanings


async def deny(persona: Persona, perception: Perception, not_granted: list[str]) -> str:
    """Generate denial text when requested tools cannot be used. Returns the message string."""
    from application.core.brain import current, ego
    logger.info("ego.deny", {"persona_id": persona.id, "not_granted": not_granted})

    sig_text = format_signals(perception.signals)
    situation_ctx = current.situation(persona, ["say"])
    system = "\n\n".join(filter(None, [
        situation_ctx,
        f"You cannot proceed because these tools require permission: {', '.join(not_granted)}. "
        "Communicate this naturally to the person given the context of the conversation.",
    ]))

    prompt = "\n".join([
        f"Impression: {perception.impression}\n",
        sig_text,
        f"\nYou cannot use these tools without permission: {', '.join(not_granted)}",
        "Tell the person honestly — explain what you were going to do and why you need their permission first.",
        'Return JSON: {"text": "your message to the person"}',
    ])

    resp = await reason(persona, prompt, system=system)
    text = resp.get("text", "") if isinstance(resp, dict) else ""
    if not text:
        text = f"I need permission to use: {', '.join(not_granted)} before I can proceed."
    return text


async def legalize(persona: Persona, steps: list[Step]) -> dict:
    """Check permissions for planned steps against the persistent permissions file."""
    logger.info("ego.legalize", {"persona_id": persona.id, "steps": len(steps)})

    tool_names = [s.tool for s in steps]
    if not tool_names:
        return {"granted": [], "rejected": [], "unknown": []}

    raw = paths.read(paths.permissions(persona.id))
    try:
        permissions_data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        permissions_data = {}
    permissions_text = (
        json.dumps(permissions_data, indent=2)
        if permissions_data
        else "(none — no permissions recorded yet)"
    )

    prompt = "\n".join([
        f"We are about to run: {', '.join(tool_names)}",
        "",
        "Permissions on file:",
        permissions_text,
        "",
        "Based on what the person has permitted or denied, decide for each tool whether it is "
        "covered (granted), ruled out (rejected), or not addressed (unknown).",
        'Return JSON: {"granted": [...], "rejected": [...], "unknown": [...]}',
        "Every tool name must appear in exactly one list.",
    ])

    resp = await reason(persona, prompt)
    if not isinstance(resp, dict):
        return {"granted": [], "rejected": [], "unknown": tool_names}

    granted = [t for t in (resp.get("granted") or []) if t in tool_names]
    rejected = [t for t in (resp.get("rejected") or []) if t in tool_names]
    unknown = [t for t in (resp.get("unknown") or []) if t in tool_names]

    accounted = set(granted + rejected + unknown)
    for t in tool_names:
        if t not in accounted:
            unknown.append(t)
    return {"granted": granted, "rejected": rejected, "unknown": unknown}


async def grant_or_reject(persona: Persona, pending_tools: list[str], signals: list[Signal]) -> dict:
    """Detect permission decisions for pending tools from the conversation and persist them."""
    from application.platform import filesystem, datetimes

    logger.info("ego.grant_or_reject", {"persona_id": persona.id, "pending": pending_tools})

    sig_text = format_signals(signals)
    prompt = "\n".join([
        f"These tools are awaiting permission: {', '.join(pending_tools)}",
        "",
        "Conversation:",
        sig_text,
        "",
        "Based on what the person said, which tools did they clearly intend to allow or deny?",
        "Only include tools where intent is unambiguous.",
        'Return JSON: {"granted": [...], "rejected": [...]}',
    ])

    resp = await reason(persona, prompt)
    if not isinstance(resp, dict):
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
        from application.platform import datetimes
        now_str = datetimes.now().strftime("%Y-%m-%d %H:%M")
        for tool in granted:
            data["granted"].append(f"{tool} (at: {now_str})")
        for tool in rejected:
            data["rejected"].append(f"{tool} (at: {now_str})")
        filesystem.write(p, json.dumps(data, indent=2))

    return {"granted": granted, "rejected": rejected}
