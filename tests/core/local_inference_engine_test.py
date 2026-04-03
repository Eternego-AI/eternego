import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from application.core import local_inference_engine
from application.platform import ollama


def test_get_default_model_returns_first_model():
    result = {}
    ollama.assert_get(
        run=lambda: _capture(result, local_inference_engine.get_default_model()),
        validate=lambda r: _assert_equal(r["path"], "/api/tags"),
        response={"models": [{"name": "llama3:latest"}, {"name": "phi4:14b"}]},
    )
    assert result["value"] == "llama3:latest"


def test_get_default_model_returns_none_when_no_models():
    result = {}
    ollama.assert_get(
        run=lambda: _capture(result, local_inference_engine.get_default_model()),
        response={"models": []},
    )
    assert result["value"] is None


def test_pull_sends_correct_model_name():
    ollama.assert_post(
        run=lambda: local_inference_engine.pull("llama3:latest"),
        validate=lambda r: (
            _assert_equal(r["path"], "/api/pull"),
            _assert_equal(r["body"]["name"], "llama3:latest"),
        ),
        response={"status": "success"},
    )


def test_register_sends_model_and_base():
    ollama.assert_post(
        run=lambda: local_inference_engine.register("primus-llama3", "llama3:latest"),
        validate=lambda r: (
            _assert_equal(r["path"], "/api/create"),
            _assert_equal(r["body"]["model"], "primus-llama3"),
            _assert_equal(r["body"]["from"], "llama3:latest"),
        ),
        response={},
    )


def test_delete_sends_correct_model():
    result = {}
    ollama.assert_delete(
        run=lambda: _capture(result, local_inference_engine.delete("llama3:latest")),
        validate=lambda r: (
            _assert_equal(r["path"], "/api/delete"),
            _assert_equal(r["body"]["name"], "llama3:latest"),
        ),
        response={},
    )
    assert result["value"] is True


def test_check_returns_true_when_model_exists_and_responds():
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"models": [{"name": "llama3:latest"}]}).encode())

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"response": "hi"}).encode())

        def log_message(self, *args): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    import asyncio
    import config.inference as cfg
    original_cfg = cfg.OLLAMA_BASE_URL
    original_mod = ollama.OLLAMA_BASE_URL
    cfg.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"
    ollama.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"

    try:
        asyncio.run(_capture(result, local_inference_engine.check("llama3:latest")))
    finally:
        cfg.OLLAMA_BASE_URL = original_cfg
        ollama.OLLAMA_BASE_URL = original_mod
        server.shutdown()

    assert result["value"] is True


def test_check_returns_false_when_model_not_in_list():
    result = {}
    ollama.assert_get(
        run=lambda: _capture(result, local_inference_engine.check("nonexistent:model")),
        response={"models": [{"name": "llama3:latest"}]},
    )
    assert result["value"] is False


async def _capture(result, coro):
    result["value"] = await coro


def _assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
