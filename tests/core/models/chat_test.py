"""chat — send messages to local, anthropic, and openai models."""

from application.platform.processes import on_separate_process_async


# ── Local ───────────────────────────────────────────────────────────────────


async def test_local_returns_content():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        result = {}
        async def run():
            result["value"] = await models.chat(Model(name="llama3"), [{"role": "user", "content": "hi"}])
        ollama.assert_call(run=run, response={"message": {"content": "Hello!"}})
        assert result["value"] == "Hello!", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_sends_correct_payload():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        def validate(r):
            assert r["path"] == "/api/chat", r["path"]
            assert r["body"]["model"] == "llama3", r["body"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]
        ollama.assert_call(
            run=lambda: models.chat(Model(name="llama3"), [{"role": "user", "content": "hi"}]),
            validate=validate,
            response={"message": {"content": "ok"}},
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
                asyncio.run(models.chat(Model(name="llama3"), [{"role": "user", "content": "hi"}]))
                assert False, "should have raised EngineConnectionError"
            except EngineConnectionError:
                pass
        finally:
            cfg.OLLAMA_BASE_URL = original_cfg
            ollama.OLLAMA_BASE_URL = original_mod
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Anthropic ───────────────────────────────────────────────────────────────


async def test_anthropic_returns_content():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", credentials={"api_key": "test"})
        result = {}
        anthropic.assert_chat(
            run=lambda: result.update(text=asyncio.run(models.chat(model, [{"role": "user", "content": "hello"}]))),
            response={"content": [{"text": "Claude says hi"}]},
        )
        assert result["text"] == "Claude says hi"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_sends_correct_model():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", credentials={"api_key": "test"})
        def validate(r):
            assert r["body"]["model"] == "claude-3", r["body"]["model"]
        anthropic.assert_chat(
            run=lambda: asyncio.run(models.chat(model, [{"role": "user", "content": "hi"}])),
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_raises_model_error_on_401():
    def isolated():
        import asyncio, json, threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import ModelError
        from application.platform import anthropic

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "invalid_api_key"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = anthropic.BASE_URL
        anthropic.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            try:
                asyncio.run(models.chat(Model(name="c", provider="anthropic", credentials={"api_key": "x"}), [{"role": "user", "content": "hi"}]))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            anthropic.BASE_URL = original
            server.shutdown()
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_raises_model_error_on_500():
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
                asyncio.run(models.chat(Model(name="c", provider="anthropic", credentials={"api_key": "x"}), [{"role": "user", "content": "hi"}]))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            anthropic.BASE_URL = original
            server.shutdown()
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── OpenAI ──────────────────────────────────────────────────────────────────


async def test_openai_returns_content():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", credentials={"api_key": "test"})
        result = {}
        openai.assert_chat(
            run=lambda: result.update(text=asyncio.run(models.chat(model, [{"role": "user", "content": "hello"}]))),
            response={"choices": [{"message": {"content": "GPT says hi"}}]},
        )
        assert result["text"] == "GPT says hi"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_sends_correct_model():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", credentials={"api_key": "test"})
        def validate(r):
            assert r["body"]["model"] == "gpt-4", r["body"]["model"]
        openai.assert_chat(
            run=lambda: asyncio.run(models.chat(model, [{"role": "user", "content": "hi"}])),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_raises_model_error_on_401():
    def isolated():
        import asyncio, json, threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import ModelError
        from application.platform import openai

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "invalid_api_key"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = openai.BASE_URL
        openai.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            try:
                asyncio.run(models.chat(Model(name="g", provider="openai", credentials={"api_key": "x"}), [{"role": "user", "content": "hi"}]))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            openai.BASE_URL = original
            server.shutdown()
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_raises_model_error_on_500():
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
                self.wfile.write(json.dumps({"error": "server_error"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = openai.BASE_URL
        openai.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            try:
                asyncio.run(models.chat(Model(name="g", provider="openai", credentials={"api_key": "x"}), [{"role": "user", "content": "hi"}]))
                assert False, "should have raised"
            except ModelError:
                pass
        finally:
            openai.BASE_URL = original
            server.shutdown()
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Thinking tag stripping ──────────────────────────────────────────────────


async def test_local_strips_thinking_tags():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        result = {}
        async def run():
            result["value"] = await models.chat(Model(name="llama3"), [{"role": "user", "content": "hi"}])
        ollama.assert_call(run=run, response={"message": {"content": "<think>reasoning here</think>Hello!"}})
        assert result["value"] == "Hello!", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_strips_multiline_thinking_tags():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        result = {}
        async def run():
            result["value"] = await models.chat(Model(name="llama3"), [{"role": "user", "content": "hi"}])
        ollama.assert_call(run=run, response={"message": {"content": "<think>\nlet me think\nabout this\n</think>\nHello!"}})
        assert result["value"] == "Hello!", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
