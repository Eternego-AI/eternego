"""OpenAI — OpenAI API communication and export parsing."""

import json


def role_based_text(data: str) -> str:
    """Parse OpenAI export into role-based text lines."""
    export = json.loads(data)
    lines = []
    for conversation in export:
        mapping = conversation.get("mapping", {})
        for node in mapping.values():
            message = node.get("message")
            if message and message.get("content", {}).get("parts"):
                role = message["author"]["role"]
                text = " ".join(message["content"]["parts"])
                lines.append(f"{role}: {text}")
    return "\n".join(lines)
