"""OpenAI — OpenAI API communication and export parsing."""

import json
import urllib.request


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


def respond(api_key: str, model: str, messages: list[dict]) -> str:
    """Send messages to the OpenAI API and return the full response text."""
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": messages,
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read())
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def stream(api_key: str, model: str, messages: list[dict]):
    """Stream a chat response from the OpenAI API, yielding normalized chunks."""
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "stream": True,
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
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
            choice = event.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            finish = choice.get("finish_reason")

            if finish:
                yield {"message": {"content": ""}, "done": True}
            elif delta.get("tool_calls"):
                yield {"message": {"content": delta.get("content", ""), "tool_calls": delta["tool_calls"]}, "done": False}
            elif delta.get("content"):
                yield {"message": {"content": delta["content"]}, "done": False}
