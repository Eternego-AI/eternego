"""generate_training_set — generate fine-tuning pairs from persona traits."""

from application.platform.processes import on_separate_process_async


async def test_local_passes_traits_in_prompt():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        result = {}

        async def run(url):
            result["value"] = await models.generate_training_set(
                Model(name="llama3", url=url),
                "You are TestBot",
                "Be concise and direct",
            )

        def validate(r):
            user_msg = r["body"]["messages"][-1]["content"]
            assert "Be concise and direct" in user_msg, "traits not in prompt"
            assert "TestBot" in user_msg, "character not in prompt"

        ollama.assert_call(
            run=run,
            validate=validate,
            responses=[[{"message": {"content": '{"training_pairs": [{"trait_source": "concise", "system": "s", "user": "u", "assistant": "a"}]}'}, "done": True}]],
        )
        assert len(result["value"]) == 1
        assert result["value"][0]["trait_source"] == "concise"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_local_returns_empty_on_invalid_json():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model

        result = {}
        async def run(url):
            result["value"] = await models.generate_training_set(Model(url=url, name="llama3"), "You are TestBot", "some traits")

        ollama.assert_call(run=run, responses=[[{"message": {"content": "not valid json at all"}, "done": True}]])
        assert result["value"] == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_passes_traits_in_prompt():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", api_key="test", url="TBD")
        result = {}
        async def run(url):
            model.url = url
            result["value"] = await models.generate_training_set(model, "You are TestBot", "Be warm and supportive")

        def validate(r):
            user_msg = r["body"]["messages"][-1]["content"]
            assert "Be warm and supportive" in user_msg, "traits not in prompt"
            assert "TestBot" in user_msg, "character not in prompt"

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": '{"training_pairs": [{"trait_source": "warm", "system": "s", "user": "u", "assistant": "a"}]}'}]},
        )
        assert len(result["value"]) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_passes_traits_in_prompt():
    def isolated():
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", api_key="test", url="TBD")
        result = {}
        async def run(url):
            model.url = url
            result["value"] = await models.generate_training_set(model, "You are TestBot", "Use humor often")

        def validate(r):
            user_msg = r["body"]["messages"][-1]["content"]
            assert "Use humor often" in user_msg, "traits not in prompt"
            assert "TestBot" in user_msg, "character not in prompt"

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": '{"training_pairs": [{"trait_source": "humor", "system": "s", "user": "u", "assistant": "a"}]}'}}]},
        )
        assert len(result["value"]) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
