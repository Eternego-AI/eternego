import json

from application.platform import openai
from application.platform.processes import on_separate_process_async


async def test_chat_sends_correct_model_and_messages():
    def isolated():
        from application.platform import openai

        def run(url):
            openai.chat(url, "test-key", "gpt-4", [{"role": "user", "content": "hi"}])

        def validate(r):
            assert r["body"]["model"] == "gpt-4", r["body"]["model"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]["messages"]

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "Hello"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_headers():
    def isolated():
        from application.platform import openai

        def run(url):
            openai.chat(url, "test-key", "gpt-4", [])

        def validate(r):
            assert r["headers"]["Authorization"] == "Bearer test-key", r["headers"]

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_returns_response_content():
    def isolated():
        from application.platform import openai

        result = {}
        def run(url):
            result["text"] = openai.chat(url, "test-key", "gpt-4", [])

        openai.assert_chat(
            run=run,
            response={"choices": [{"message": {"content": "Hello from GPT"}}]},
        )
        assert result["text"] == "Hello from GPT", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_parses_json_response():
    def isolated():
        from application.platform import openai

        result = {}
        def run(url):
            result["data"] = openai.chat_json(url, "test-key", "gpt-4", [])

        openai.assert_chat_json(
            run=run,
            response={"choices": [{"message": {"content": '{"result": true}'}}]},
        )
        assert result["data"] == {"result": True}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_generate_sends_prompt_as_user_message():
    def isolated():
        from application.platform import openai

        def run(url):
            openai.generate(url, "test-key", "gpt-4", "Write something")

        def validate(r):
            assert r["body"]["messages"] == [{"role": "user", "content": "Write something"}], r["body"]

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "  generated text  "}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_hits_correct_path():
    def isolated():
        from application.platform import openai

        def run(url):
            openai.chat(url, "key", "gpt-4", [])

        def validate(r):
            assert r["path"] == "/v1/chat/completions", r["path"]

        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_sends_json_mode_flag():
    def isolated():
        from application.platform import openai

        def run(url):
            openai.chat_json(url, "key", "gpt-4", [{"role": "user", "content": "json"}])

        def validate(r):
            assert r["body"]["response_format"] == {"type": "json_object"}, r["body"]

        openai.assert_chat_json(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_returns_empty_on_invalid():
    def isolated():
        from application.platform import openai

        result = {}
        def run(url):
            result["data"] = openai.chat_json(url, "key", "gpt-4", [])

        openai.assert_chat_json(
            run=run,
            response={"choices": [{"message": {"content": "not json"}}]},
        )
        assert result["data"] == {}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_passes_system_messages_in_messages():
    def isolated():
        from application.platform import openai

        def run(url):
            openai.chat(url, "key", "gpt-4", [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "hi"},
            ])

        def validate(r):
            assert r["body"]["messages"] == [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "hi"},
            ], r["body"]["messages"]
        openai.assert_chat(
            run=run,
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_generate_json_returns_parsed_json():
    def isolated():
        from application.platform import openai

        result = {}
        def run(url):
            result["data"] = openai.generate_json(url, "key", "gpt-4", "give json")

        openai.assert_chat_json(
            run=run,
            response={"choices": [{"message": {"content": '{"n": 1}'}}]},
        )
        assert result["data"] == {"n": 1}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_generate_json_returns_empty_on_invalid():
    def isolated():
        from application.platform import openai

        result = {}
        def run(url):
            result["data"] = openai.generate_json(url, "key", "gpt-4", "give json")

        openai.assert_chat_json(
            run=run,
            response={"choices": [{"message": {"content": "nope"}}]},
        )
        assert result["data"] == {}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_generate_strips_whitespace():
    def isolated():
        from application.platform import openai

        result = {}
        def run(url):
            result["text"] = openai.generate(url, "key", "gpt-4", "write")

        openai.assert_chat(
            run=run,
            response={"choices": [{"message": {"content": "  hello  "}}]},
        )
        assert result["text"] == "hello", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


def test_to_messages_parses_nested_export():
    export = json.dumps([
        {"mapping": {
            "node1": {"message": {"author": {"role": "user"}, "content": {"parts": ["Hello world"]}}},
            "node2": {"message": {"author": {"role": "assistant"}, "content": {"parts": ["Hi", "there"]}}},
        }}
    ])
    result = openai.to_messages(export)
    assert {"role": "user", "content": "Hello world"} in result
    assert {"role": "assistant", "content": "Hi there"} in result


def test_to_messages_skips_system_role():
    export = json.dumps([
        {"mapping": {"node1": {"message": {"author": {"role": "system"}, "content": {"parts": ["prompt"]}}}}}
    ])
    result = openai.to_messages(export)
    assert len(result) == 0


def test_to_messages_handles_empty_export():
    result = openai.to_messages("[]")
    assert result == []
