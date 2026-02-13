"""Anthropic — Anthropic API communication and export parsing."""

import json
import urllib.request


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


def stream(api_key: str, model: str, messages: list[dict]):
    """Stream a chat response from the Anthropic API, yielding normalized chunks."""
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "stream": True,
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(request) as response:
        for line in response:
            line = line.decode().strip()
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            event = json.loads(data)
            event_type = event.get("type", "")

            if event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield {"message": {"content": delta.get("text", "")}, "done": False}
                elif delta.get("type") == "input_json_delta":
                    yield {"message": {"content": "", "tool_calls": [delta]}, "done": False}
            elif event_type == "message_stop":
                yield {"message": {"content": ""}, "done": True}
