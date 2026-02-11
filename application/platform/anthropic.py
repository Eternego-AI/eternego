"""Anthropic — Anthropic API communication and export parsing."""

import json


def role_based_text(data: str) -> str:
    """Parse Anthropic export into role-based text lines."""
    export = json.loads(data)
    lines = []
    for conversation in export:
        for message in conversation.get("chat_messages", []):
            role = message.get("sender", "unknown")
            text = message.get("text", "")
            lines.append(f"{role}: {text}")
    return "\n".join(lines)
