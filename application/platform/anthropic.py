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


def chat(api_key: str, model: str, messages: list[dict], json_mode: bool = False) -> str:
    """Send a list of messages to the Anthropic API and return the response text."""
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "format": "json" if json_mode else "text",
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read())
        return data.get("content", [{}])[0].get("text", "")


def chat_json(api_key: str, model: str, messages: list[dict]) -> dict:
    """Send a list of messages to the Anthropic API and return the parsed JSON response."""
    response = chat(api_key, model, messages, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}


def generate(api_key: str, model: str, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the Anthropic API and return the response text."""
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "format": "json" if json_mode else "text",
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read())
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip()

def generate_json(api_key: str, model: str, prompt: str) -> dict:
    """Send a prompt to the Anthropic API and return the parsed JSON response."""
    response = generate(api_key, model, prompt, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}

