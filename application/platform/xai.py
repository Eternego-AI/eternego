"""xAI — Grok API communication. OpenAI-compatible apart from no stream_options."""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

from application.platform import logger
from application.platform.observer import send, dispatch, Message, Plan

BASE_URL = "https://api.x.ai"


async def chat(base_url: str, api_key: str | None, model: str, messages: list[dict]):
    """Stream chat response, yielding content chunks."""
    api_key = api_key or ""
    url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    body = {"model": model, "messages": messages, "stream": True}
    dispatch(Plan("Sending xAI Request", {"url": url, "headers": {**headers, "Authorization": "Bearer ***"}, "body": body}))
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", url, json=body, headers=headers) as response:
                if response.status_code >= 400:
                    body_bytes = await response.aread()
                    body_text = body_bytes.decode("utf-8", errors="replace")
                    logger.warning("xAI API error", {
                        "status": response.status_code,
                        "model": model,
                        "body": body_text,
                    })
                    raise OSError(f"xAI HTTP {response.status_code}: {body_text}")
                yielded = False
                usage = {}
                try:
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
                        if event.get("error"):
                            err = event["error"]
                            message = err.get("message", "unknown error") if isinstance(err, dict) else str(err)
                            logger.warning("xAI stream error event", {"model": model, "error": err})
                            raise OSError(f"xAI stream error: {message}")
                        if event.get("usage"):
                            usage = event["usage"]
                        choices = event.get("choices", [])
                        if not choices:
                            continue
                        content = choices[0].get("delta", {}).get("content", "")
                        if content:
                            yielded = True
                            await send(Message("xAI stream chunk received", {"chunk": content}))
                            yield content
                finally:
                    if yielded:
                        cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) if usage else 0
                        dispatch(Message("Model usage", {
                            "provider": "xai",
                            "model": model,
                            "input_tokens": usage.get("prompt_tokens", 0),
                            "output_tokens": usage.get("completion_tokens", 0),
                            "cache_read_tokens": cached,
                            "cache_write_tokens": 0,
                        }))
                if not yielded:
                    raise OSError("xAI returned empty response")
    except httpx.RequestError as e:
        logger.warning("xAI transport error", {"model": model, "error": str(e)})
        raise ConnectionError(str(e)) from e


async def chat_json(base_url: str, api_key: str | None, model: str, messages: list[dict]):
    """Stream JSON response, yielding content chunks.

    xAI's function-calling implementation leaks chat template tokens
    (`<|tool_calls_section_begin|>...`) into the content stream when
    `tool_choice` forces a specific function — server-side quirk, not
    fixable on our end. So xAI does not accept a `tools` argument; it
    uses `response_format: json_object` to force valid JSON and lets
    the caller's prompt carry the shape.
    """
    api_key = api_key or ""
    url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    body = {"model": model, "messages": messages, "stream": True, "response_format": {"type": "json_object"}}
    dispatch(Plan("Sending xAI Request", {"url": url, "headers": {**headers, "Authorization": "Bearer ***"}, "body": body}))
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", url, json=body, headers=headers) as response:
                if response.status_code >= 400:
                    body_bytes = await response.aread()
                    body_text = body_bytes.decode("utf-8", errors="replace")
                    logger.warning("xAI API error", {
                        "status": response.status_code,
                        "model": model,
                        "body": body_text,
                    })
                    raise OSError(f"xAI HTTP {response.status_code}: {body_text}")
                yielded = False
                usage = {}
                try:
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
                        if event.get("error"):
                            err = event["error"]
                            message = err.get("message", "unknown error") if isinstance(err, dict) else str(err)
                            logger.warning("xAI stream error event", {"model": model, "error": err})
                            raise OSError(f"xAI stream error: {message}")
                        if event.get("usage"):
                            usage = event["usage"]
                        choices = event.get("choices", [])
                        if not choices:
                            continue
                        chunk = choices[0].get("delta", {}).get("content", "")
                        if chunk:
                            yielded = True
                            await send(Message("xAI stream chunk received", {"chunk": chunk}))
                            yield chunk
                finally:
                    if yielded:
                        cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) if usage else 0
                        dispatch(Message("Model usage", {
                            "provider": "xai",
                            "model": model,
                            "input_tokens": usage.get("prompt_tokens", 0),
                            "output_tokens": usage.get("completion_tokens", 0),
                            "cache_read_tokens": cached,
                            "cache_write_tokens": 0,
                        }))
                if not yielded:
                    raise OSError("xAI returned empty response")
    except httpx.RequestError as e:
        logger.warning("xAI transport error", {"model": model, "error": str(e)})
        raise ConnectionError(str(e)) from e


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_chat(run, validate=None, response=None, status_code=200):
    """Run chat against a local SSE server."""
    text = response.get("choices", [{}])[0].get("message", {}).get("content", "") if response else ""
    assert_call(run, validate, text, status_code)


def assert_chat_json(run, validate=None, response=None, status_code=200):
    """Run tool against a local SSE server."""
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
