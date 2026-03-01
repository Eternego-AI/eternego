"""OpenAI — OpenAI API communication and export parsing."""

import json
import os
import urllib.request

_TIMEOUT: int = int(os.environ.get("OPENAI_TIMEOUT", "30"))


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


def chat(api_key: str, model: str, messages: list[dict], json_mode: bool = False) -> str:
    """Send messages to the OpenAI API and return the response text."""
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "format": "json" if json_mode else "text",
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        data = json.loads(response.read())
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def chat_json(api_key: str, model: str, messages: list[dict]) -> dict:
    """Send messages to the OpenAI API and return the parsed JSON response."""
    response = chat(api_key, model, messages, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}


def generate(api_key: str, model: str, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the OpenAI API and return the response text."""
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json" if json_mode else "text",
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        data = json.loads(response.read())
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip()


def generate_json(api_key: str, model: str, prompt: str) -> dict:
    """Send a prompt to the OpenAI API and return the parsed JSON response."""
    response = generate(api_key, model, prompt, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}
