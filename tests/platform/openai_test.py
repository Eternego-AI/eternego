import json

from application.platform import openai
from application.platform.processes import on_separate_process_async


async def test_chat_sends_correct_model_and_messages():
    def isolated():
        from application.platform import openai
        def validate(r):
            assert r["body"]["model"] == "gpt-4", r["body"]["model"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]["messages"]
        openai.assert_chat(
            run=lambda: openai.chat("test-key", "gpt-4", [{"role": "user", "content": "hi"}]),
            validate=validate,
            response={"choices": [{"message": {"content": "Hello"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_headers():
    def isolated():
        from application.platform import openai
        def validate(r):
            assert r["headers"]["Authorization"] == "Bearer my-api-key", r["headers"]
        openai.assert_chat(
            run=lambda: openai.chat("my-api-key", "gpt-4", []),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_returns_response_content():
    def isolated():
        from application.platform import openai
        result = {}
        openai.assert_chat(
            run=lambda: result.update(text=openai.chat("key", "gpt-4", [])),
            response={"choices": [{"message": {"content": "Hello from GPT"}}]},
        )
        assert result["text"] == "Hello from GPT", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_parses_json_response():
    def isolated():
        from application.platform import openai
        result = {}
        openai.assert_chat_json(
            run=lambda: result.update(data=openai.chat_json("key", "gpt-4", [])),
            response={"choices": [{"message": {"content": '{"result": true}'}}]},
        )
        assert result["data"] == {"result": True}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_generate_sends_prompt_as_user_message():
    def isolated():
        from application.platform import openai
        def validate(r):
            assert r["body"]["messages"] == [{"role": "user", "content": "Write something"}], r["body"]
        openai.assert_chat(
            run=lambda: openai.generate("key", "gpt-4", "Write something"),
            validate=validate,
            response={"choices": [{"message": {"content": "  generated text  "}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_hits_correct_path():
    def isolated():
        from application.platform import openai
        def validate(r):
            assert r["path"] == "/v1/chat/completions", r["path"]
        openai.assert_chat(
            run=lambda: openai.chat("key", "gpt-4", []),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
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
