"""Anthropic — Anthropic API communication and export parsing."""

import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler


BASE_URL = "https://api.anthropic.com"


def chat(api_key: str, model: str, messages: list[dict]) -> str:
    """Send a list of messages to the Anthropic API and return the response text."""
    system_parts = []
    chat_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m.get("content", ""))
        else:
            chat_messages.append(m)

    body = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": 4096,
    }
    if system_parts:
        body["system"] = "\n".join(system_parts)

    req = urllib.request.Request(
        f"{BASE_URL}/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req) as response:
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


async def async_chat(api_key: str, model: str, messages: list[dict]) -> str:
    """Async version of chat — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(chat, api_key, model, messages)


async def async_chat_json(api_key: str, model: str, messages: list[dict]) -> dict:
    """Async version of chat_json — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(chat_json, api_key, model, messages)


async def async_chat_stream(api_key: str, model: str, messages: list[dict]) -> str:
    """Stream response from Anthropic API, return full text. Cancellable at each chunk."""
    import httpx

    system_parts = []
    chat_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m.get("content", ""))
        else:
            chat_messages.append(m)

    body = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": 4096,
        "stream": True,
    }
    if system_parts:
        body["system"] = "\n".join(system_parts)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", f"{BASE_URL}/v1/messages", json=body, headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }) as response:
                response.raise_for_status()
                parts = []
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    try:
                        event = json.loads(line[6:].strip())
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta":
                        parts.append(event.get("delta", {}).get("text", ""))
                    if event.get("type") == "message_stop":
                        break
                return "".join(parts)
    except httpx.HTTPStatusError as e:
        raise OSError(f"HTTP {e.response.status_code}") from e


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


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_chat(run, validate=None, response=None):
    """Run chat against a local server, validate the request, return controlled response."""
    assert_call(run, validate, response or {"content": [{"text": ""}]})


def assert_chat_json(run, validate=None, response=None):
    """Run chat_json against a local server, validate the request, return controlled response."""
    assert_call(run, validate, response or {"content": [{"text": "{}"}]})


def assert_call(run, validate, response_body):
    global BASE_URL
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received["body"] = body
            received["headers"] = dict(self.headers)
            received["path"] = self.path
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_body).encode())
        def log_message(self, *args): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    original = BASE_URL
    BASE_URL = f"http://127.0.0.1:{port}"

    try:
        run()
        if validate:
            validate(received)
    finally:
        BASE_URL = original
        server.shutdown()
