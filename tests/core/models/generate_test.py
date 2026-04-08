"""generate — send prompt and return text for all model kinds."""

from application.platform.processes import on_separate_process_async


# ── Local ───────────────────────────────────────────────────────────────────


async def test_local_returns_stripped_response():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        result = {}
        async def run():
            result["value"] = await models.generate(Model(name="llama3"), "prompt")
        ollama.assert_call(run=run, response={"response": "  generated text  "})
        assert result["value"] == "generated text", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_sends_correct_payload():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        def validate(r):
            assert r["path"] == "/api/generate", r["path"]
            assert r["body"]["model"] == "llama3", r["body"]
            assert r["body"]["prompt"] == "hello", r["body"]
        ollama.assert_call(
            run=lambda: models.generate(Model(name="llama3"), "hello"),
            validate=validate,
            response={"response": "ok"},
        )
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
                asyncio.run(models.generate(Model(name="llama3"), "hi"))
                assert False, "should have raised"
            except EngineConnectionError:
                pass
        finally:
            cfg.OLLAMA_BASE_URL = original_cfg
            ollama.OLLAMA_BASE_URL = original_mod
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Anthropic ───────────────────────────────────────────────────────────────


async def test_anthropic_delegates_to_chat():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", credentials={"api_key": "test"})
        result = {}
        def validate(r):
            assert r["body"]["messages"] == [{"role": "user", "content": "write something"}], r["body"]
        anthropic.assert_chat(
            run=lambda: result.update(text=asyncio.run(models.generate(model, "write something"))),
            validate=validate,
            response={"content": [{"text": "generated"}]},
        )
        assert result["text"] == "generated"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


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
                self.send_response(403)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "forbidden"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = anthropic.BASE_URL
        anthropic.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            try:
                asyncio.run(models.generate(Model(name="c", provider="anthropic", credentials={"api_key": "x"}), "hi"))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            anthropic.BASE_URL = original
            server.shutdown()
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── OpenAI ──────────────────────────────────────────────────────────────────


async def test_openai_delegates_to_chat():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", credentials={"api_key": "test"})
        result = {}
        def validate(r):
            assert r["body"]["messages"] == [{"role": "user", "content": "write something"}], r["body"]
        openai.assert_chat(
            run=lambda: result.update(text=asyncio.run(models.generate(model, "write something"))),
            validate=validate,
            response={"choices": [{"message": {"content": "generated"}}]},
        )
        assert result["text"] == "generated"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


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
                self.send_response(403)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "forbidden"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = openai.BASE_URL
        openai.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            try:
                asyncio.run(models.generate(Model(name="g", provider="openai", credentials={"api_key": "x"}), "hi"))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            openai.BASE_URL = original
            server.shutdown()
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
