"""generate_training_set — generate fine-tuning pairs from DNA."""

from application.platform.processes import on_separate_process_async


async def test_local_passes_dna_in_prompt():
    def isolated():
        from application.platform import ollama
        from application.core import models
        from application.core.data import Model
        result = {}

        def validate(r):
            assert "Be concise and direct" in r["body"]["prompt"], "DNA not in prompt"

        async def run():
            result["value"] = await models.generate_training_set(
                Model(name="llama3"),
                "Be concise and direct",
            )

        ollama.assert_call(
            run=run,
            validate=validate,
            response={"response": '{"training_pairs": [{"trait_source": "concise", "system": "s", "user": "u", "assistant": "a"}]}'},
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

        async def run():
            result["value"] = await models.generate_training_set(Model(name="llama3"), "some dna")

        ollama.assert_call(run=run, response={"response": "not valid json at all"})
        assert result["value"] == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_anthropic_passes_dna_in_prompt():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", credentials={"api_key": "test"})
        result = {}

        def validate(r):
            user_msg = r["body"]["messages"][0]["content"]
            assert "Be warm and supportive" in user_msg, "DNA not in prompt"

        anthropic.assert_chat(
            run=lambda: result.update(value=asyncio.run(models.generate_training_set(model, "Be warm and supportive"))),
            validate=validate,
            response={"content": [{"text": '{"training_pairs": [{"trait_source": "warm", "system": "s", "user": "u", "assistant": "a"}]}'}]},
        )
        assert len(result["value"]) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_openai_passes_dna_in_prompt():
    def isolated():
        import asyncio
        from application.core import models
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", credentials={"api_key": "test"})
        result = {}

        def validate(r):
            user_msg = r["body"]["messages"][0]["content"]
            assert "Use humor often" in user_msg, "DNA not in prompt"

        openai.assert_chat(
            run=lambda: result.update(value=asyncio.run(models.generate_training_set(model, "Use humor often"))),
            validate=validate,
            response={"choices": [{"message": {"content": '{"training_pairs": [{"trait_source": "humor", "system": "s", "user": "u", "assistant": "a"}]}'}}]},
        )
        assert len(result["value"]) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
