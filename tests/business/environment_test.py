import os
import json
import asyncio
import tempfile
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

from application.business import environment
from application.core import agents, gateways, paths
from application.core.data import Channel, Model, Persona
from application.core.brain.data import Meaning
from application.platform import ollama
import config.inference as cfg


_original_home = os.environ.get("HOME")


class FakeWorker:
    def __init__(self):
        self.stopped = False
    def run(self, *args): pass
    def nudge(self): pass


class TestMeaning(Meaning):
    name = "Test"
    def description(self): return "Test"
    def clarify(self): return None
    def reply(self): return "Reply"
    def path(self): return None
    def summarize(self): return None


def _setup():
    tmp = tempfile.mkdtemp()
    os.environ["HOME"] = tmp
    agents._personas.clear()
    gateways._active.clear()
    subprocess.run(["git", "config", "--global", "user.email", "test@test.com"], env={**os.environ, "HOME": tmp})
    subprocess.run(["git", "config", "--global", "user.name", "Test"], env={**os.environ, "HOME": tmp})


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home
    agents._personas.clear()
    gateways._active.clear()


def _fake_ollama_server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path == "/api/chat":
                self.wfile.write(json.dumps({"message": {"content": "ok"}}).encode())
            elif self.path == "/api/generate":
                self.wfile.write(json.dumps({"response": "ok"}).encode())
            else:
                self.wfile.write(json.dumps({"status": "success"}).encode())
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"models": [{"name": "llama3"}]}).encode())
        def log_message(self, *a): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _with_fake_ollama(fn):
    server = _fake_ollama_server()
    port = server.server_address[1]
    original_cfg = cfg.OLLAMA_BASE_URL
    original_mod = ollama.OLLAMA_BASE_URL
    cfg.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"
    ollama.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"
    try:
        return fn()
    finally:
        cfg.OLLAMA_BASE_URL = original_cfg
        ollama.OLLAMA_BASE_URL = original_mod
        server.shutdown()


# ── ready ────────────────────────────────────────────────────────────────────

def test_ready_succeeds_when_engine_serving():
    _setup()
    result = _with_fake_ollama(lambda: asyncio.run(environment.ready()))
    assert result.success is True
    _teardown()


# ── check_model ──────────────────────────────────────────────────────────────

def test_check_model_succeeds():
    _setup()
    result = {}
    ollama.assert_call(
        run=lambda: _capture(result, environment.check_model("llama3")),
        responses=[
            {"models": [{"name": "llama3"}]},
            {"response": "ok"},
        ],
    )
    assert result["value"].success is True
    _teardown()


def test_check_model_fails_when_not_found():
    _setup()
    result = {}
    ollama.assert_call(
        run=lambda: _capture(result, environment.check_model("nonexistent")),
        response={"models": [{"name": "llama3"}]},
    )
    assert result["value"].success is False
    _teardown()


# ── pair ─────────────────────────────────────────────────────────────────────

def test_pair_claims_code():
    _setup()
    from application.business import persona as spec

    def run():
        create_result = asyncio.run(spec.create(
            name="PairBot", model="llama3", channel_type="telegram",
            channel_credentials={"token": "fake"},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]
        find_result = asyncio.run(spec.find(persona_id))
        persona = find_result.data["persona"]

        code = agents.pair(persona, Channel(type="telegram", name="12345"))
        return asyncio.run(environment.pair(code))

    result = _with_fake_ollama(run)
    assert result.success is True
    assert "persona_id" in result.data
    _teardown()


def test_pair_fails_on_invalid_code():
    _setup()
    result = asyncio.run(environment.pair("INVALID"))
    assert result.success is False
    _teardown()


async def _capture(result, coro):
    result["value"] = await coro
