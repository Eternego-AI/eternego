"""Anthropic — Anthropic API communication and export parsing."""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

from application.platform import logger
from application.platform.observer import send, dispatch, Message, Plan

BASE_URL = "https://api.anthropic.com"


async def chat(base_url: str, api_key: str | None, model: str, messages: list[dict]):
    """Stream chat response, yielding content chunks."""
    api_key = api_key or ""
    system_blocks = []
    chat_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_blocks.append(m)
        else:
            chat_messages.append(m)

    body = {"model": model, "messages": chat_messages, "max_tokens": 4096, "stream": True}
    has_cache = False
    if system_blocks:
        blocks = []
        for sys_msg in system_blocks:
            block = {"type": "text", "text": sys_msg.get("content", "")}
            cache_type = sys_msg.get("cache_control")
            if cache_type:
                has_cache = True
                block["cache_control"] = {"type": cache_type, "ttl": "1h"}
            blocks.append(block)
        body["system"] = blocks

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
            msg["content"] = [
                *content[:-1],
                {**content[-1], "cache_control": {"type": cache_type, "ttl": "1h"}},
            ]

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    if has_cache:
        headers["anthropic-beta"] = "extended-cache-ttl-2025-04-11"

    url = f"{base_url}/v1/messages"
    dispatch(Plan("Sending Anthropic Request", {"url": url, "headers": {**headers, "x-api-key": "***"}, "body": body}))
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", url, json=body, headers=headers) as response:
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


async def chat_json(base_url: str, api_key: str | None, model: str, messages: list[dict], tools: list[dict] | None = None, tool_choice: dict | None = None):
    """Stream JSON response, yielding content chunks.

    Anthropic has no JSON-mode flag; the API-level way to force JSON is
    `tool_use`. When the caller provides `tools` (and optionally
    `tool_choice`), they are passed through to the API verbatim and the
    model emits via `input_json_delta`. Without them this becomes a
    plain chat — useful for callers that want the streaming machinery
    without structured-output constraints.
    """
    api_key = api_key or ""
    system_blocks = []
    chat_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_blocks.append(m)
        else:
            chat_messages.append(m)

    body: dict = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": 4096,
        "stream": True,
    }
    if tools is not None:
        body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
    has_cache = False
    if system_blocks:
        blocks = []
        for sys_msg in system_blocks:
            block = {"type": "text", "text": sys_msg.get("content", "")}
            cache_type = sys_msg.get("cache_control")
            if cache_type:
                has_cache = True
                block["cache_control"] = {"type": cache_type, "ttl": "1h"}
            blocks.append(block)
        body["system"] = blocks

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
            msg["content"] = [
                *content[:-1],
                {**content[-1], "cache_control": {"type": cache_type, "ttl": "1h"}},
            ]

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    if has_cache:
        headers["anthropic-beta"] = "extended-cache-ttl-2025-04-11"

    url = f"{base_url}/v1/messages"
    dispatch(Plan("Sending Anthropic Request", {"url": url, "headers": {**headers, "x-api-key": "***"}, "body": body}))
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", url, json=body, headers=headers) as response:
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
                stop_reason: str | None = None
                event_types: list[str] = []
                delta_types: list[str] = []
                content_block_types: list[str] = []
                first_tool_input = None
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    try:
                        event = json.loads(line[6:].strip())
                    except json.JSONDecodeError:
                        continue
                    etype = event.get("type")
                    if etype and (not event_types or event_types[-1] != etype):
                        event_types.append(etype)
                    if etype == "error":
                        err = event.get("error", {})
                        message = err.get("message", "unknown error")
                        logger.warning("Anthropic stream error event", {"model": model, "error": err})
                        raise OSError(f"Anthropic stream error: {message}")
                    if etype == "message_start":
                        msg_usage = event.get("message", {}).get("usage", {})
                        usage.update(msg_usage)
                    if etype == "message_delta":
                        delta_usage = event.get("usage", {})
                        usage.update(delta_usage)
                        new_stop = event.get("delta", {}).get("stop_reason")
                        if new_stop:
                            stop_reason = new_stop
                    if etype == "content_block_start":
                        block = event.get("content_block", {})
                        ctype = block.get("type")
                        if ctype and (not content_block_types or content_block_types[-1] != ctype):
                            content_block_types.append(ctype)
                        if ctype == "tool_use" and first_tool_input is None:
                            first_tool_input = block.get("input")
                    if etype == "content_block_delta":
                        delta = event.get("delta", {})
                        dtype = delta.get("type")
                        if dtype and (not delta_types or delta_types[-1] != dtype):
                            delta_types.append(dtype)
                        chunk = delta.get("partial_json") or delta.get("text", "")
                        if chunk:
                            yielded = True
                            await send(Message("Anthropic stream chunk received", {"chunk": chunk}))
                            yield chunk
                    if etype == "message_stop":
                        break
                if not yielded and "tool_use" in content_block_types and first_tool_input is not None:
                    # When the model commits to a small or empty tool input,
                    # Anthropic ships the full input in `content_block_start`
                    # and emits empty `input_json_delta` heartbeats. Surface
                    # the upfront input as the JSON chunk so the caller parses
                    # normally. An empty `{}` is a valid no-action response;
                    # recognize/decide handle empty dicts as "rest this beat."
                    fallback = json.dumps(first_tool_input)
                    yielded = True
                    logger.debug("Anthropic tool input from content_block_start", {"model": model, "input": first_tool_input})
                    await send(Message("Anthropic stream chunk received", {"chunk": fallback}))
                    yield fallback

                if not yielded:
                    err = OSError("Anthropic returned empty response")
                    err.details = {
                        "stop_reason": stop_reason,
                        "event_types": event_types,
                        "content_block_types": content_block_types,
                        "delta_types": delta_types,
                        "first_tool_input": first_tool_input,
                        "usage": usage,
                    }
                    raise err
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
    """Run chat_json against a local SSE server.

    Response shapes:
    - `response={"tool_use_input": "<json>"}` — input_json_delta stream
      (used when caller passes `tools`).
    - `response={"content": [{"text": "..."}]}` — text_delta stream
      (used when caller omits `tools`; plain chat fallback).
    """
    if response and "tool_use_input" in response:
        assert_call(run, validate, response["tool_use_input"], status_code, mode="input_json")
        return
    text = response.get("content", [{}])[0].get("text", "") if response else ""
    assert_call(run, validate, text, status_code, mode="text")


def assert_call(run, validate, response_text, status_code=200, mode="text"):
    """Run async code against a local SSE streaming server.

    `mode` controls the delta shape: "text" (text_delta) or "input_json"
    (input_json_delta).
    """
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
                if mode == "input_json":
                    delta = {"type": "input_json_delta", "partial_json": response_text}
                else:
                    delta = {"text": response_text}
                event = {"type": "content_block_delta", "delta": delta}
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
