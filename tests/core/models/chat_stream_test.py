"""chat_stream — stream and return text for all model kinds."""

from application.platform.processes import on_separate_process_async


# ── Local ───────────────────────────────────────────────────────────────────


async def test_local_streams_and_returns_text():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        text = "Hello, person."
        chunks = [{"message": {"content": c}} for c in text]

        result = {}
        async def run(url):
            result["value"] = await models.chat_stream(Model(name="llama3", url=url), [{"role": "user", "content": "hi"}])

        ollama.assert_call(run=run, response=chunks)
        assert result["value"] == text, result["value"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_raises_engine_error_on_connection_failure():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import EngineConnectionError

        try:
            asyncio.run(models.chat_stream(Model(name="llama3", url="http://127.0.0.1:1"), []))
            assert False, "should have raised"
        except EngineConnectionError:
            pass

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_strips_thinking_tags():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        thinking_then_text = '<think>let me reason about this</think>The answer is 42.'
        chunks = [{"message": {"content": c}} for c in thinking_then_text]

        result = {}
        async def run(url):
            result["value"] = await models.chat_stream(Model(name="llama3", url=url), [])

        ollama.assert_call(run=run, response=chunks)
        assert result["value"] == "The answer is 42.", result["value"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Anthropic ───────────────────────────────────────────────────────────────


async def test_anthropic_raises_model_error_on_http_error():
    def isolated():
        import application.platform.anthropic as anthropic
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import ModelError
            try:
                await models.chat_stream(Model(name="c", provider="anthropic", api_key="x", url=url), [])
                assert False, "Expected ModelError"
            except ModelError:
                pass

        anthropic.assert_call(
            run=run,
            validate=None,
            response_body={"error": "internal"},
            status_code=500,
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── OpenAI ──────────────────────────────────────────────────────────────────


async def test_openai_raises_model_error_on_http_error():
    def isolated():
        from application.platform import openai
        from application.core import models
        from application.core.data import Model


        async def run(url):
            from application.core.exceptions import ModelError
            try:
                await models.chat_stream(Model(name="g", provider="openai", api_key="x", url=url), [])
                assert False, "Expected ModelError"
            except ModelError:
                pass

        openai.assert_call(
            run=run,
            validate=None,
            response_body={"error": "internal"},
            status_code=500,
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
