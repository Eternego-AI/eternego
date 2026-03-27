"""Perceptions — formatting helpers for Perception nodes."""

from application.core.brain.data import Signal, SignalEvent, Perception


def narrate(signals: list[Signal]) -> str:
    """Narrate a list of signals as a scene description from the persona's perspective."""
    lines = []
    for s in signals:
        ts = s.created_at.strftime("%Y-%m-%d %H:%M UTC")
        channel = f" through {s.channel_type}" if s.channel_type else ""
        if s.event == SignalEvent.heard:
            lines.append(f"The person said{channel} at {ts}: {s.content}")
        elif s.event == SignalEvent.queried:
            lines.append(f"A system queried on behalf of the person at {ts}: {s.content}")
        elif s.event == SignalEvent.nudged:
            lines.append(f"You received an internal nudge at {ts}: {s.content}")
        elif s.event == SignalEvent.answered:
            lines.append(f"You replied{channel} at {ts}: {s.content}")
        elif s.event == SignalEvent.clarified:
            lines.append(f"You informed the person{channel} at {ts}: {s.content}")
        elif s.event == SignalEvent.decided:
            lines.append(f"You decided at {ts}: {s.content}")
        elif s.event == SignalEvent.executed:
            lines.append(f"Following your decision, the system returned at {ts}: {s.content}")
        elif s.event == SignalEvent.recap:
            lines.append(f"You concluded this matter at {ts}: {s.content}")
        elif s.event == SignalEvent.summarized:
            lines.append(f"You summarized to the person{channel} at {ts}: {s.content}")
        else:
            lines.append(f"[{ts}] {s.event}: {s.content}")
    return "\n".join(lines)


def conversation(perception: Perception) -> str:
    """Return only the person-visible exchange — for chat UI and archive."""
    visible = (SignalEvent.heard, SignalEvent.queried, SignalEvent.answered, SignalEvent.clarified, SignalEvent.summarized)
    lines = []
    for s in perception.thread:
        if s.event not in visible:
            continue
        ts = s.created_at.strftime("%Y-%m-%d %H:%M UTC")
        who = "person" if s.event in (SignalEvent.heard, SignalEvent.queried) else "persona"
        lines.append(f"[{ts}] {who}: {s.content}")
    return "\n".join(lines)


def thread(perception: Perception) -> str:
    """Return a full string representation of a perception and its thread."""
    lines = [f"# {perception.impression}"]
    for s in perception.thread:
        ts = s.created_at.strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"[{ts}] {s.event}: {s.content}")
    return "\n".join(lines)


def to_conversation(signals: list[Signal]) -> list[dict]:
    """Only what was said — no tool mechanics. Coalesces consecutive same-role messages."""
    messages = []
    for s in signals:
        if s.event in (SignalEvent.heard, SignalEvent.queried, SignalEvent.nudged):
            role = "user"
        elif s.event in (SignalEvent.answered, SignalEvent.clarified, SignalEvent.summarized):
            role = "assistant"
        else:
            continue

        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + s.content
        else:
            messages.append({"role": role, "content": s.content})
    return messages


def to_messages(signals: list[Signal]) -> list[dict]:
    """Full thread including tool results — for pipeline steps that need execution context.

    Coalesces consecutive same-role messages.
    """
    messages = []
    for s in signals:
        if s.event in (SignalEvent.heard, SignalEvent.queried, SignalEvent.nudged, SignalEvent.executed):
            role = "user"
        elif s.event in (SignalEvent.answered, SignalEvent.clarified, SignalEvent.summarized):
            role = "assistant"
        else:
            continue

        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + s.content
        else:
            messages.append({"role": role, "content": s.content})
    return messages
