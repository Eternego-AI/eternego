"""chat_json_stream — stream and return parsed JSON for all model kinds."""

from application.platform.processes import on_separate_process_async


# ── Local ───────────────────────────────────────────────────────────────────


async def test_local_streams_and_parses_json():
    def isolated():
        import json
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        result = {}

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        async def run():
            result["value"] = await models.chat_json_stream(Model(name="llama3"), [{"role": "user", "content": "json"}])

        ollama.assert_call(run=run, response=stream_json({"answer": 42}))
        assert result["value"] == {"answer": 42}, result["value"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_raises_engine_error_on_connection_failure():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import EngineConnectionError
        from application.platform import ollama
        import config.inference as cfg

        original_cfg = cfg.OLLAMA_BASE_URL
        original_mod = ollama.OLLAMA_BASE_URL
        cfg.OLLAMA_BASE_URL = "http://127.0.0.1:1"
        ollama.OLLAMA_BASE_URL = "http://127.0.0.1:1"
        try:
            try:
                asyncio.run(models.chat_json_stream(Model(name="llama3"), []))
                assert False, "should have raised"
            except EngineConnectionError:
                pass
        finally:
            cfg.OLLAMA_BASE_URL = original_cfg
            ollama.OLLAMA_BASE_URL = original_mod

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_strips_thinking_tags():
    def isolated():
        import json
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        result = {}

        thinking_then_json = '<think>let me reason about this</think>{"answer": 42}'
        chunks = [{"message": {"content": c}} for c in thinking_then_json]

        async def run():
            result["value"] = await models.chat_json_stream(Model(name="llama3"), [])

        ollama.assert_call(run=run, response=chunks)
        assert result["value"] == {"answer": 42}, result["value"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Anthropic ───────────────────────────────────────────────────────────────


async def test_anthropic_raises_model_error_on_http_error():
    def isolated():
        import asyncio, json, threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import ModelError
        from application.platform import anthropic

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "internal"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = anthropic.BASE_URL
        anthropic.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            try:
                asyncio.run(models.chat_json_stream(Model(name="c", provider="anthropic", credentials={"api_key": "x"}), []))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            anthropic.BASE_URL = original
            server.shutdown()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── OpenAI ──────────────────────────────────────────────────────────────────


async def test_openai_raises_model_error_on_http_error():
    def isolated():
        import asyncio, json, threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import ModelError
        from application.platform import openai

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "internal"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = openai.BASE_URL
        openai.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            try:
                asyncio.run(models.chat_json_stream(Model(name="g", provider="openai", credentials={"api_key": "x"}), []))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            openai.BASE_URL = original
            server.shutdown()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
