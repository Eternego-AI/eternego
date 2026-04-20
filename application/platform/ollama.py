"""Ollama — local model communication."""

import json
import threading

import httpx

from config.inference import OLLAMA_BASE_URL
from http.server import HTTPServer, BaseHTTPRequestHandler
from application.platform.observer import send, Message


class OllamaError(Exception):
    """The Ollama server returned an error response."""
    pass


async def is_serving() -> bool:
    """Check if the Ollama server is responding."""
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=httpx.Timeout(None, connect=10.0)) as http:
            response = await http.get("/")
            return response.status_code == 200
    except httpx.RequestError:
        return False


async def get(base_url: str, path: str) -> dict:
    """Send a GET request to the Ollama API."""
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(None, connect=10.0)) as http:
            response = await http.get(path)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def post(base_url: str, path: str, data: dict) -> dict:
    """Send a POST request to the Ollama API."""
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(None, connect=10.0)) as http:
            response = await http.post(path, json=data)
            response.raise_for_status()
            body = response.text.strip()
            return response.json() if body else {}
    except httpx.HTTPStatusError as e:
        raise OllamaError(f"Ollama API error {e.response.status_code}: {e.response.text}") from e
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def delete(base_url: str, path: str, data: dict) -> dict:
    """Send a DELETE request to the Ollama API."""
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(None, connect=10.0)) as http:
            response = await http.request("DELETE", path, json=data)
            response.raise_for_status()
            body = response.text.strip()
            return response.json() if body else {}
    except httpx.HTTPStatusError as e:
        raise OllamaError(f"Ollama API error {e.response.status_code}: {e.response.text}") from e
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def stream(base_url: str, path: str, data: dict):
    """Send a POST request and yield JSON chunks as they arrive.

    Raises OllamaError if the server responds with an HTTP error or emits an
    `error` field in any chunk (e.g. model load failure). Raises ConnectionError
    on transport-level failures (cannot connect, read timeout, protocol error).
    """
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", path, json=data) as response:
                if response.status_code >= 400:
                    body_bytes = await response.aread()
                    body_text = body_bytes.decode("utf-8", errors="replace")
                    raise OllamaError(f"HTTP {response.status_code}: {body_text}")
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("error"):
                        raise OllamaError(str(chunk["error"]))
                    yield chunk
    except httpx.RequestError as e:
        raise ConnectionError(str(e)) from e


async def chat(base_url: str, model: str, messages: list[dict]):
    """Stream chat response, yielding content chunks.

    Raises OllamaError if the stream ends without yielding any content
    (happens when ollama accepts the request but fails to load the model,
    e.g. out-of-memory — the API returns an empty stream).
    """
    body = {"model": model, "messages": messages}
    yielded = False
    async for chunk in stream(base_url, "/api/chat", body):
        content = chunk.get("message", {}).get("content", "")
        if content:
            yielded = True
            await send(Message("Ollama stream chunk received", {"chunk": content}))
            yield content
    if not yielded:
        raise OllamaError("empty response from ollama (model may have failed to load)")


async def chat_json(base_url: str, model: str, messages: list[dict]):
    """Stream JSON chat response, yielding content chunks. Uses format:json constraint.

    Raises OllamaError on empty streams — see chat() for why.
    """
    body = {"model": model, "messages": messages, "format": "json"}
    yielded = False
    async for chunk in stream(base_url, "/api/chat", body):
        content = chunk.get("message", {}).get("content", "")
        if content:
            yielded = True
            await send(Message("Ollama stream chunk received", {"chunk": content}))
            yield content
    if not yielded:
        raise OllamaError("empty response from ollama (model may have failed to load)")


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_post(run, validate=None, response=None, status_code=200):
    """Run an async function against a local server, validate the POST request."""
    assert_call(run, validate, response or {}, None, status_code)


def assert_get(run, validate=None, response=None, status_code=200):
    """Run an async function against a local server, validate the GET request."""
    assert_call(run, validate, response or {}, None, status_code)


def assert_delete(run, validate=None, response=None, status_code=200):
    """Run an async function against a local server, validate the DELETE request."""
    assert_call(run, validate, response or {}, None, status_code)


def assert_call(run, validate=None, response=None, responses=None, status_code=200):
    """Run async code against a local server.

    response: single dict for regular requests.
    responses: list of dicts, served in order for sequential requests.
               Each can be a dict (single JSON) or a list (streaming chunks).
    """
    import asyncio
    import inspect

    if responses is None and response is not None:
        responses = [response]
    elif responses is None:
        responses = [{}]

    received_list = []
    call_index = [0]

    class Handler(BaseHTTPRequestHandler):
        def _handle(self):
            content_length = self.headers.get("Content-Length")
            body = None
            if content_length:
                body = json.loads(self.rfile.read(int(content_length)))
            received_list.append({"body": body, "path": self.path, "method": self.command, "headers": dict(self.headers)})

            idx = min(call_index[0], len(responses) - 1)
            resp = responses[idx]
            call_index[0] += 1

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            if isinstance(resp, list):
                for chunk in resp:
                    self.wfile.write((json.dumps(chunk) + "\n").encode())
            else:
                self.wfile.write(json.dumps(resp).encode())

        def do_POST(self): self._handle()
        def do_GET(self): self._handle()
        def do_DELETE(self): self._handle()
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
