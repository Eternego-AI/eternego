"""Anthropic — Anthropic API communication and export parsing."""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

from application.platform import logger
from application.platform.observer import send, dispatch, Message

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
    has_cache = False
    if system_parts:
        text = "\n".join(system_parts)
        cache_type = next((m.get("cache_control") for m in messages if m.get("role") == "system" and m.get("cache_control")), None)
        if cache_type:
            has_cache = True
            body["system"] = [{"type": "text", "text": text, "cache_control": {"type": cache_type, "ttl": "1h"}}]
        else:
            body["system"] = text

    for msg in chat_messages:
        cache_type = msg.pop("cache_control", None)
        if not cache_type:
            continue
        has_cache = True
        content = msg.get("content", "")
        if isinstance(content, str):
            msg["content"] = [
                {"type": "text", "text": content, "cache_control": {"type": cache_type, "ttl": "1h"}},
            ]
        elif isinstance(content, list) and content:
            content[-1]["cache_control"] = {"type": cache_type, "ttl": "1h"}

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    if has_cache:
        headers["anthropic-beta"] = "extended-cache-ttl-2025-04-11"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", f"{base_url}/v1/messages", json=body, headers=headers) as response:
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
                usage = {}
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
                    if event.get("type") == "message_start":
                        msg_usage = event.get("message", {}).get("usage", {})
                        usage.update(msg_usage)
                    if event.get("type") == "message_delta":
                        delta_usage = event.get("usage", {})
                        usage.update(delta_usage)
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
                dispatch(Message("Model usage", {
                    "provider": "anthropic",
                    "model": model,
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                    "cache_write_tokens": usage.get("cache_creation_input_tokens", 0),
                }))
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
