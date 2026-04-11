"""OpenAI — OpenAI API communication and export parsing."""

import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler


BASE_URL = "https://api.openai.com"
_TIMEOUT = 120


def chat(base_url: str, api_key: str | None, model: str, messages: list[dict], json_mode: bool = False) -> str:
    """Send messages to the OpenAI API and return the response text."""
    api_key = api_key or ""
    payload = {
        "model": model,
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
            data = json.loads(response.read())
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise OSError(f"HTTP {e.code}: {body}") from e


def chat_json(base_url: str, api_key: str, model: str, messages: list[dict]) -> dict:
    """Send messages to the OpenAI API and return the parsed JSON response."""
    response = chat(base_url, api_key, model, messages, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}


def generate(base_url: str, api_key: str, model: str, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the OpenAI API and return the response text."""
    return chat(base_url, api_key, model, [{"role": "user", "content": prompt}], json_mode).strip()


def generate_json(base_url: str, api_key: str, model: str, prompt: str) -> dict:
    """Send a prompt to the OpenAI API and return the parsed JSON response."""
    response = generate(base_url, api_key, model, prompt, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}


async def async_chat(base_url: str, api_key: str, model: str, messages: list[dict]) -> str:
    """Async version of chat — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(chat, base_url, api_key, model, messages)


async def async_chat_json(base_url: str, api_key: str, model: str, messages: list[dict]) -> dict:
    """Async version of chat_json — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(chat_json, base_url, api_key, model, messages)


async def async_chat_stream(base_url: str, api_key: str | None, model: str, messages: list[dict]) -> str:
    """Stream response from OpenAI API, return full text. Cancellable at each chunk."""
    import httpx

    api_key = api_key or ""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", f"{base_url}/v1/chat/completions", json={
                "model": model,
                "messages": messages,
                "stream": True,
            }, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }) as response:
                response.raise_for_status()
                parts = []
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = event.get("choices", [])
                    if not choices:
                        continue
                    content = choices[0].get("delta", {}).get("content", "")
                    if content:
                        parts.append(content)
                return "".join(parts)
    except httpx.HTTPStatusError as e:
        raise OSError(f"HTTP {e.response.status_code}") from e


def to_messages(data: str) -> list[dict]:
    """Parse OpenAI export into role-based messages."""
    export = json.loads(data)
    messages = []
    for conversation in export:
        mapping = conversation.get("mapping", {})
        for node in mapping.values():
            message = node.get("message")
            if message and message.get("content", {}).get("parts"):
                role = message["author"]["role"]
                if role not in ("user", "assistant"):
                    continue
                text = " ".join(message["content"]["parts"])
                messages.append({"role": role, "content": text})
    return messages


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_chat(run, validate=None, response=None, status_code=200):
    """Run chat against a local server, validate the request, return controlled response."""
    assert_call(run, validate, response or {"choices": [{"message": {"content": ""}}]}, status_code=status_code)


def assert_chat_json(run, validate=None, response=None, status_code=200):
    """Run chat_json against a local server, validate the request, return controlled response."""
    assert_call(run, validate, response or {"choices": [{"message": {"content": "{}"}}]}, status_code=status_code)


def assert_call(run, validate, response_body, status_code=200):
    import asyncio
    import inspect

    global BASE_URL
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received["body"] = body
            received["headers"] = dict(self.headers)
            received["path"] = self.path
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_body).encode())
        def log_message(self, *args): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    url = f"http://127.0.0.1:{port}"

    try:
        result = run(url)
        if inspect.iscoroutine(result):
            asyncio.run(result)
        if validate:
            validate(received)
    finally:
        server.shutdown()
