"""chat — send messages to local, anthropic, and openai models."""
from wsgiref import validate

from application.platform.processes import on_separate_process_async


# ── Local ───────────────────────────────────────────────────────────────────


async def test_local_returns_content():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        result = {}
        async def run(url):
            result["value"] = await models.chat(Model(name="llama3", url=url), [], "hi")

        ollama.assert_call(run=run, response={"message": {"content": "Hello!"}})
        assert result["value"] == "Hello!", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_sends_correct_payload():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        async def run(url):
            await models.chat(Model(name="llama3", url=url), [], "hi")

        def validate(r):
            assert r["path"] == "/api/chat", r["path"]
            assert r["body"]["model"] == "llama3", r["body"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]

        ollama.assert_call(
            run=run,
            validate=validate,
            response={"message": {"content": "ok"}},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_raises_engine_error_on_empty_stream():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import EngineConnectionError

        async def run(url):
            try:
                await models.chat(Model(name="llama3", url=url), [], "hi")
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        ollama.assert_call(run=run, responses=[[]])
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_raises_engine_error_on_error_chunk():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import EngineConnectionError

        async def run(url):
            try:
                await models.chat(Model(name="llama3", url=url), [], "hi")
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        ollama.assert_call(
            run=run,
            responses=[[{"error": "model requires more system memory"}]],
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_raises_engine_error_on_connection_failure():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import EngineConnectionError

        url = "http://127.0.0.1:1"
        try:
            asyncio.run(models.chat(Model(name="llama3", url=url), [], "hi"))
            assert False, "should have raised EngineConnectionError"
        except EngineConnectionError:
            pass
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Anthropic ───────────────────────────────────────────────────────────────


async def test_anthropic_returns_content():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        result = {}
        async def run(url):
            model = Model(name="claude-3", provider="anthropic", api_key="test", url=url)
            result["text"] = await models.chat(model, [], "hello")
        
        anthropic.assert_chat(
            run=run,
            response={"content": [{"text": "Claude says hi"}]},
        )
        assert result["text"] == "Claude says hi"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_sends_correct_model():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", api_key="test", url="TBD")
        async def run(url):
            model.url = url
            await models.chat(model, [], "hi")

        def validate(r):
            assert r["body"]["model"] == "claude-3", r["body"]["model"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_raises_engine_error_on_401():
    def isolated():
        import application.platform.anthropic as anthropic
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import EngineConnectionError
            try:
                await models.chat(
                    Model(name="c", provider="anthropic", api_key="x", url=url),
                    [], "hi"
                )
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        def validate(r):
            pass

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": ""}]},
            status_code=401,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_raises_engine_error_on_500():
    def isolated():
        import application.platform.anthropic as anthropic
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import EngineConnectionError
            try:
                await models.chat(
                    Model(name="c", provider="anthropic", api_key="x", url=url),
                    [], "hi"
                )
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        def validate(r):
            pass

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": ""}]},
            status_code=500,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── OpenAI ──────────────────────────────────────────────────────────────────


async def test_openai_returns_content():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", api_key="test", url="TBD")
        result = {}
        async def run(url):
            model.url = url
            result["text"] = await models.chat(model, [], "hello")
        
        openai.assert_chat(
            run=run,
            response={"choices": [{"message": {"content": "GPT says hi"}}]},
        )
        assert result["text"] == "GPT says hi"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_sends_correct_model():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", api_key="test", url="TBD")
        async def run(url):
            model.url = url
            await models.chat(model, [], "hi")

        def validate(r):
            assert r["body"]["model"] == "gpt-4", r["body"]["model"]

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_raises_engine_error_on_401():
    def isolated():
        from application.platform import openai
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import EngineConnectionError
            try:
                await models.chat(
                    Model(name="g", provider="openai", api_key="x", url=url),
                    [], "hi"
                )
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        def validate(r):
            pass

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": ""}}]},
            status_code=401,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_raises_engine_error_on_500():
    def isolated():
        from application.platform import openai
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import EngineConnectionError
            try:
                await models.chat(
                    Model(name="g", provider="openai", api_key="x", url=url),
                    [], "hi"
                )
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        def validate(r):
            pass

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": ""}}]},
            status_code=500,
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── xAI ─────────────────────────────────────────────────────────────────────


async def test_xai_routes_to_xai_module():
    """provider='xai' must dispatch to xai.py — not the openai catch-all path.
    Detected by absence of stream_options in the request body, since xai.py
    omits it (the field that was triggering xAI's silent connection drops)."""
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import xai

        model = Model(name="grok-4.3", provider="xai", api_key="test", url="TBD")
        async def run(url):
            model.url = url
            await models.chat(model, [], "hi")

        def validate(r):
            assert "stream_options" not in r["body"], \
                f"xai routing leaked into openai code path; stream_options in body: {r['body']}"
            assert r["body"]["model"] == "grok-4.3", r["body"]["model"]
            assert r["body"]["stream"] is True, r["body"]

        xai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_xai_returns_content():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import xai

        model = Model(name="grok-4.3", provider="xai", api_key="test", url="TBD")
        result = {}
        async def run(url):
            model.url = url
            result["text"] = await models.chat(model, [], "hi")

        xai.assert_chat(
            run=run,
            response={"choices": [{"message": {"content": "Grok says hi"}}]},
        )
        assert result["text"] == "Grok says hi"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_xai_chat_json_routes_to_xai_module():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import xai

        model = Model(name="grok-4.3", provider="xai", api_key="test", url="TBD")
        async def run(url):
            model.url = url
            await models.chat_json(model, [], "json please")

        def validate(r):
            assert "stream_options" not in r["body"], r["body"]
            assert r["body"]["response_format"] == {"type": "json_object"}, r["body"]
            assert r["body"]["model"] == "grok-4.3", r["body"]

        xai.assert_chat_json(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_xai_raises_engine_error_on_401():
    def isolated():
        from application.platform import xai
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import EngineConnectionError
            try:
                await models.chat(
                    Model(name="grok-4.3", provider="xai", api_key="x", url=url),
                    [], "hi"
                )
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        xai.assert_chat(
            run=run,
            response={"choices": [{"message": {"content": ""}}]},
            status_code=401,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_xai_raises_engine_error_on_500():
    def isolated():
        from application.platform import xai
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import EngineConnectionError
            try:
                await models.chat(
                    Model(name="grok-4.3", provider="xai", api_key="x", url=url),
                    [], "hi"
                )
                assert False, "Expected EngineConnectionError"
            except EngineConnectionError:
                pass

        xai.assert_chat(
            run=run,
            response={"choices": [{"message": {"content": ""}}]},
            status_code=500,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Thinking tag stripping ──────────────────────────────────────────────────


async def test_local_strips_thinking_tags():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        result = {}
        async def run(url):
            result["value"] = await models.chat(Model(name="llama3", url=url), [], "hi")

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
        async def run(url):
            result["value"] = await models.chat(Model(name="llama3", url=url), [], "hi")

        ollama.assert_call(run=run, response={"message": {"content": "<think>\nlet me think\nabout this\n</think>\nHello!"}})
        assert result["value"] == "Hello!", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
