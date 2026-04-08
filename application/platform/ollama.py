"""Ollama — local model communication: serve, pull, generate, model management."""

import json
import threading

import httpx

from config.inference import OLLAMA_BASE_URL
from http.server import HTTPServer, BaseHTTPRequestHandler


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


async def get(path: str) -> dict:
    """Send a GET request to the Ollama API."""
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=httpx.Timeout(None, connect=10.0)) as http:
            response = await http.get(path)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def post(path: str, data: dict) -> dict:
    """Send a POST request to the Ollama API."""
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=httpx.Timeout(None, connect=10.0)) as http:
            response = await http.post(path, json=data)
            response.raise_for_status()
            body = response.text.strip()
            return response.json() if body else {}
    except httpx.HTTPStatusError as e:
        raise OllamaError(f"Ollama API error {e.response.status_code}: {e.response.text}") from e
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def delete(path: str, data: dict) -> dict:
    """Send a DELETE request to the Ollama API."""
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=httpx.Timeout(None, connect=10.0)) as http:
            response = await http.request("DELETE", path, json=data)
            response.raise_for_status()
            body = response.text.strip()
            return response.json() if body else {}
    except httpx.HTTPStatusError as e:
        raise OllamaError(f"Ollama API error {e.response.status_code}: {e.response.text}") from e
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def stream(path: str, data: dict):
    """Send a POST request and yield JSON chunks as they arrive."""
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=httpx.Timeout(None, connect=10.0)) as http:
            async with http.stream("POST", path, json=data) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        yield json.loads(line)
    except httpx.ConnectError as e:
        raise ConnectionError(str(e)) from e


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_post(run, validate=None, response=None):
    """Run an async function against a local server, validate the POST request."""
    assert_call(run, validate, response or {})


def assert_get(run, validate=None, response=None):
    """Run an async function against a local server, validate the GET request."""
    assert_call(run, validate, response or {})


def assert_delete(run, validate=None, response=None):
    """Run an async function against a local server, validate the DELETE request."""
    assert_call(run, validate, response or {})


def assert_call(run, validate=None, response=None, responses=None):
    """Run async code against a local server.

    response: single dict for regular requests.
    responses: list of dicts, served in order for sequential requests.
               Each can be a dict (single JSON) or a list (streaming chunks).
    """
    import asyncio

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
            received_list.append({"body": body, "path": self.path, "method": self.command})

            idx = min(call_index[0], len(responses) - 1)
            resp = responses[idx]
            call_index[0] += 1

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            if isinstance(resp, list):
                # Streaming: each item is a line-delimited JSON chunk
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

    import config.inference as cfg
    original = cfg.OLLAMA_BASE_URL
    cfg.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"

    global OLLAMA_BASE_URL
    original_module = OLLAMA_BASE_URL
    OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"

    try:
        asyncio.run(run())
        if validate:
            validate(received_list[0] if len(received_list) == 1 else received_list)
    finally:
        cfg.OLLAMA_BASE_URL = original
        OLLAMA_BASE_URL = original_module
        server.shutdown()
