"""chat_json — send messages and return parsed JSON for all model kinds."""

from application.platform.processes import on_separate_process_async


# ── Local ───────────────────────────────────────────────────────────────────


async def test_local_parses_json():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        result = {}
        async def run(url):
            result["value"] = await models.chat_json(Model(name="llama3", url=url), [])

        ollama.assert_call(run=run, response={"message": {"content": '{"answer": 42}'}})

        assert result["value"] == {"answer": 42}, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_raises_engine_error_on_connection_failure():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.core.exceptions import EngineConnectionError

        try:
            asyncio.run(models.chat_json(Model(name="llama3", url="http://127.0.0.1:1"), []))
            assert False, "should have raised"
        except EngineConnectionError:
            pass
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Anthropic ───────────────────────────────────────────────────────────────


async def test_anthropic_returns_parsed_json():
    def isolated():
        from application.platform import anthropic
        from application.core import models
        from application.core.data import Model

        result = {}
        async def run(url):
            model = Model(name="claude-3", provider="anthropic", credentials={"api_key": "test"}, url=url)
            result["data"] = await models.chat_json(model, [{"role": "user", "content": "json"}])
        
        anthropic.assert_chat_json(
            run=run,
            response={"content": [{"text": '{"answer": 42}'}]},
        )
        assert result["data"] == {"answer": 42}
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_raises_model_error_on_http_error():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        async def run(url):
            from application.core.exceptions import ModelError
            try:
                await models.chat_json(Model(name="c", provider="anthropic", credentials={"api_key": "x"}, url=url), [])
                assert False, "Expected ModelError"
            except ModelError:
                pass

        anthropic.assert_call(
            run=run,
            validate=None,
            response_body={"error": "rate_limited"},
            status_code=429,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── OpenAI ──────────────────────────────────────────────────────────────────


async def test_openai_returns_parsed_json():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        result = {}
        async def run(url):
            model = Model(name="gpt-4", provider="openai", credentials={"api_key": "test"}, url=url)
            result["data"] = await models.chat_json(model, [{"role": "user", "content": "json"}])
        
        openai.assert_chat_json(
            run=run,
            response={"choices": [{"message": {"content": '{"answer": 42}'}}]},
        )
        assert result["data"] == {"answer": 42}
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_raises_model_error_on_http_error():
    def isolated():
        from application.platform import openai
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import ModelError
            try:
                await models.chat_json(Model(name="g", provider="openai", credentials={"api_key": "x"}, url=url), [])
                assert False, "Expected ModelError"
            except ModelError:
                pass

        openai.assert_call(
            run=run,
            validate=None,
            response_body={"error": "rate_limited"},
            status_code=429,
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Thinking tag stripping ──────────────────────────────────────────────────


async def test_local_strips_thinking_tags_before_parsing():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        result = {}
        async def run(url):
            result["value"] = await models.chat_json(Model(name="llama3", url=url), [])

        ollama.assert_call(run=run, response={"message": {"content": '<think>reasoning</think>{"answer": 42}'}})
        assert result["value"] == {"answer": 42}, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
