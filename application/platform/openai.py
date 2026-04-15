"""OpenAI — OpenAI-compatible API communication and export parsing."""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

from application.platform.observer import send, Message

BASE_URL = "https://api.openai.com"


async def chat(base_url: str, api_key: str | None, model: str, messages: list[dict]):
    """Stream chat response, yielding content chunks."""
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
                        await send(Message("OpenAI stream chunk received", {"chunk": content}))
                        yield content
    except httpx.HTTPStatusError as e:
        raise OSError(f"HTTP {e.response.status_code}") from e


async def chat_json(base_url: str, api_key: str | None, model: str, messages: list[dict]):
    """Stream JSON chat response, yielding content chunks. Uses response_format constraint."""
    api_key = api_key or ""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", f"{base_url}/v1/chat/completions", json={
                "model": model,
                "messages": messages,
                "stream": True,
                "response_format": {"type": "json_object"},
            }, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }) as response:
                response.raise_for_status()
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
                        await send(Message("OpenAI stream chunk received", {"chunk": content}))
                        yield content
    except httpx.HTTPStatusError as e:
        raise OSError(f"HTTP {e.response.status_code}") from e


def to_messages(data: str) -> list[list[dict]]:
    """Parse OpenAI export into conversations, each a list of role-based messages."""
    export = json.loads(data)
    conversations = []
    for conversation in export:
        messages = []
        mapping = conversation.get("mapping", {})
        for node in mapping.values():
            message = node.get("message")
            if message and message.get("content", {}).get("parts"):
                role = message["author"]["role"]
                if role not in ("user", "assistant"):
                    continue
                text = " ".join(message["content"]["parts"])
                messages.append({"role": role, "content": text})
        if messages:
            conversations.append(messages)
    return conversations


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_chat(run, validate=None, response=None, status_code=200):
    """Run chat against a local SSE server."""
    text = response.get("choices", [{}])[0].get("message", {}).get("content", "") if response else ""
    assert_call(run, validate, text, status_code)


def assert_chat_json(run, validate=None, response=None, status_code=200):
    """Run chat_json against a local SSE server."""
    text = response.get("choices", [{}])[0].get("message", {}).get("content", "") if response else ""
    assert_call(run, validate, text, status_code)


def assert_call(run, validate, response_text, status_code=200):
    """Run async code against a local SSE streaming server."""
    import asyncio
    import inspect

    received_list = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = self.headers.get("Content-Length")
            body = None
            if content_length:
                body = json.loads(self.rfile.read(int(content_length)))
            received_list.append({"body": body, "path": self.path, "method": "POST", "headers": dict(self.headers)})

            self.send_response(status_code)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()

            if response_text:
                event = {"choices": [{"delta": {"content": response_text}}]}
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.write("data: [DONE]\n\n".encode())

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
            validate(received_list[0] if len(received_list) == 1 else received_list)
    finally:
        server.shutdown()
