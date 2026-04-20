"""Anthropic — Anthropic API communication and export parsing."""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

from application.platform import logger
from application.platform.observer import send, Message

BASE_URL = "https://api.anthropic.com"


async def chat(base_url: str, api_key: str | None, model: str, messages: list[dict]):
    """Stream chat response, yielding content chunks."""
    api_key = api_key or ""
    system_parts = []
    chat_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m.get("content", ""))
        else:
            chat_messages.append(m)

    body = {"model": model, "messages": chat_messages, "max_tokens": 4096, "stream": True}
    if system_parts:
        body["system"] = "\n".join(system_parts)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", f"{base_url}/v1/messages", json=body, headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }) as response:
                if response.status_code >= 400:
                    body_bytes = await response.aread()
                    body_text = body_bytes.decode("utf-8", errors="replace")
                    logger.warning("Anthropic API error", {
                        "status": response.status_code,
                        "model": model,
                        "body": body_text,
                    })
                    raise OSError(f"Anthropic HTTP {response.status_code}: {body_text}")
                yielded = False
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    try:
                        event = json.loads(line[6:].strip())
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "error":
                        err = event.get("error", {})
                        message = err.get("message", "unknown error")
                        logger.warning("Anthropic stream error event", {"model": model, "error": err})
                        raise OSError(f"Anthropic stream error: {message}")
                    if event.get("type") == "content_block_delta":
                        text = event.get("delta", {}).get("text", "")
                        if text:
                            yielded = True
                            await send(Message("Anthropic stream chunk received", {"chunk": text}))
                            yield text
                    if event.get("type") == "message_stop":
                        break
                if not yielded:
                    raise OSError("Anthropic returned empty response")
    except httpx.RequestError as e:
        logger.warning("Anthropic transport error", {"model": model, "error": str(e)})
        raise ConnectionError(str(e)) from e


async def chat_json(base_url: str, api_key: str | None, model: str, messages: list[dict]):
    """Stream JSON chat response, yielding content chunks. No format constraint (Anthropic does not support it)."""
    async for chunk in chat(base_url, api_key, model, messages):
        yield chunk


def to_messages(data: str) -> list[list[dict]]:
    """Parse Anthropic export into conversations, each a list of role-based messages."""
    export = json.loads(data)
    conversations = []
    for conversation in export:
        messages = []
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
        if messages:
            conversations.append(messages)
    return conversations


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_chat(run, validate=None, response=None, status_code=200):
    """Run chat against a local SSE server."""
    text = response.get("content", [{}])[0].get("text", "") if response else ""
    assert_call(run, validate, text, status_code)


def assert_chat_json(run, validate=None, response=None, status_code=200):
    """Run chat_json against a local SSE server."""
    text = response.get("content", [{}])[0].get("text", "") if response else ""
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
                event = {"type": "content_block_delta", "delta": {"text": response_text}}
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            stop = {"type": "message_stop"}
            self.wfile.write(f"data: {json.dumps(stop)}\n\n".encode())

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
