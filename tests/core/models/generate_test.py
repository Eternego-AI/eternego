"""generate — send prompt and return text for all model kinds."""

from application.platform.processes import on_separate_process_async


# ── Local ───────────────────────────────────────────────────────────────────


async def test_local_returns_stripped_response():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        result = {}
        async def run(url):
            result["value"] = await models.generate(Model(name="llama3", url=url), "prompt")

        ollama.assert_call(run=run, response={"response": "  generated text  "})
        assert result["value"] == "generated text", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_sends_correct_payload():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        async def run(url):
            await models.generate(Model(name="llama3", url=url), "hello")

        def validate(r):
            assert r["path"] == "/api/generate", r["path"]
            assert r["body"]["model"] == "llama3", r["body"]
            assert r["body"]["prompt"] == "hello", r["body"]

        ollama.assert_call(
            run=run,
            validate=validate,
            response={"response": "ok"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Anthropic ───────────────────────────────────────────────────────────────


async def test_anthropic_delegates_to_chat():
    def isolated():

        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", api_key="test", url="TBD")
        result = {}
        async def run(url):
            model.url = url
            result["text"] = await models.generate(model, "write something")
        
        def validate(r):
            assert r["body"]["messages"] == [{"role": "user", "content": "write something"}], r["body"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": "generated"}]},
        )
        assert result["text"] == "generated"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_raises_model_error_on_http_error():
    def isolated():
        from application.platform import anthropic
        from application.core import models
        from application.core.data import Model

        async def run(url):
            from application.core.exceptions import ModelError
            try:
                await models.generate(Model(name="g", provider="openai", api_key="x", url=url), "hi")
                assert False, "Expected ModelError"
            except ModelError:
                pass

        anthropic.assert_call(
            run=run,
            validate=None,
            response_body={"error": "forbidden"},
            status_code=403
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── OpenAI ──────────────────────────────────────────────────────────────────


async def test_openai_delegates_to_chat():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", api_key="test", url="TBD")
        result = {}
        async def run(url):
            model.url = url
            result["text"] = await models.generate(model, "write something")
        
        def validate(r):
            assert r["body"]["messages"] == [{"role": "user", "content": "write something"}], r["body"]

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "generated"}}]},
        )
        assert result["text"] == "generated"
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
                await models.generate(Model(name="g", provider="openai", api_key="x", url=url), "hi")
                assert False, "Expected ModelError"
            except ModelError:
                pass

        openai.assert_call(
            run=run,
            validate=None,
            response_body={"error": "forbidden"},
            status_code=403
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
