"""Anthropic — Anthropic API communication and export parsing."""

import json
import urllib.error
import urllib.request


def to_messages(data: str) -> list[dict]:
    """Parse Anthropic export into role-based messages."""
    export = json.loads(data)
    messages = []
    for conversation in export:
        for message in conversation.get("chat_messages", []):
            role = message.get("sender", "unknown")
            if role == "human":
                role = "user"
            elif role == "assistant":
                pass
            else:
                continue
            text = message.get("text", "")
            messages.append({"role": role, "content": text})
    return messages


def chat(api_key: str, model: str, messages: list[dict]) -> str:
    """Send a list of messages to the Anthropic API and return the response text."""
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read())
            return data.get("content", [{}])[0].get("text", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise OSError(f"HTTP {e.code}: {body}") from e


def chat_json(api_key: str, model: str, messages: list[dict]) -> dict:
    """Send a list of messages to the Anthropic API and return the parsed JSON response."""
    from application.platform import strings
    response = chat(api_key, model, messages)
    try:
        return strings.extract_json(response)
    except json.JSONDecodeError:
        return {}

