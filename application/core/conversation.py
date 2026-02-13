"""Conversation — thread management and persistence."""

import json
from datetime import date

from application.platform import logger, filesystem
from application.core.data import Persona, Thread


def todays(persona: Persona) -> Thread:
    """Load or create today's conversation thread."""
    path = persona.storage_dir / "conversations" / f"{date.today()}.jsonl"
    messages = []
    if path.exists():
        content = filesystem.read(path)
        for line in content.splitlines():
            if line.strip():
                messages.append(json.loads(line))
    logger.info("Thread loaded", {"persona_id": persona.id, "date": str(date.today())})
    return Thread(path=path, messages=messages)


def person_said(thread: Thread, prompt: str) -> None:
    """Add a user message to the thread."""
    thread.messages.append({"role": "user", "content": prompt})
    save(thread)


def persona_replied(thread: Thread, content: str) -> None:
    """Append a text chunk to the current assistant message, or start a new one."""
    if thread.messages and thread.messages[-1].get("role") == "assistant":
        thread.messages[-1]["content"] += content
    else:
        thread.messages.append({"role": "assistant", "content": content})
    save(thread)


def persona_ended(thread: Thread, content: str) -> None:
    """Finalize the assistant message with any remaining content."""
    if content:
        if thread.messages and thread.messages[-1].get("role") == "assistant":
            thread.messages[-1]["content"] += content
        else:
            thread.messages.append({"role": "assistant", "content": content})
    save(thread)


def tool_resulted(thread: Thread, tool_calls: list[dict], result: str) -> None:
    """Add tool calls to the current assistant message and append the tool result."""
    if thread.messages and thread.messages[-1].get("role") == "assistant":
        thread.messages[-1]["tool_calls"] = tool_calls
    else:
        thread.messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
    thread.messages.append({"role": "tool", "content": result})
    save(thread)


def save(thread: Thread) -> None:
    """Save conversation to file, excluding system messages."""
    filesystem.ensure_dir(thread.path.parent)
    lines = []
    for msg in thread.messages:
        if msg.get("role") != "system":
            lines.append(json.dumps(msg))
    filesystem.write(thread.path, "\n".join(lines) + "\n")
