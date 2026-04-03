import json

from application.platform import openai


def test_chat_sends_correct_model_and_messages():
    openai.assert_chat(
        run=lambda: openai.chat("test-key", "gpt-4", [{"role": "user", "content": "hi"}]),
        validate=lambda r: (
            assert_equal(r["body"]["model"], "gpt-4"),
            assert_equal(r["body"]["messages"], [{"role": "user", "content": "hi"}]),
        ),
        response={"choices": [{"message": {"content": "Hello"}}]},
    )


def test_chat_sends_correct_headers():
    openai.assert_chat(
        run=lambda: openai.chat("my-api-key", "gpt-4", []),
        validate=lambda r: (
            assert_equal(r["headers"]["Authorization"], "Bearer my-api-key"),
        ),
        response={"choices": [{"message": {"content": "ok"}}]},
    )


def test_chat_returns_response_content():
    result = {}
    openai.assert_chat(
        run=lambda: result.update(text=openai.chat("key", "gpt-4", [])),
        response={"choices": [{"message": {"content": "Hello from GPT"}}]},
    )
    assert result["text"] == "Hello from GPT"


def test_chat_json_parses_json_response():
    result = {}
    openai.assert_chat_json(
        run=lambda: result.update(data=openai.chat_json("key", "gpt-4", [])),
        response={"choices": [{"message": {"content": '{"result": true}'}}]},
    )
    assert result["data"] == {"result": True}


def test_generate_sends_prompt_as_user_message():
    openai.assert_chat(
        run=lambda: openai.generate("key", "gpt-4", "Write something"),
        validate=lambda r: assert_equal(r["body"]["messages"], [{"role": "user", "content": "Write something"}]),
        response={"choices": [{"message": {"content": "  generated text  "}}]},
    )


def test_chat_hits_correct_path():
    openai.assert_chat(
        run=lambda: openai.chat("key", "gpt-4", []),
        validate=lambda r: assert_equal(r["path"], "/v1/chat/completions"),
        response={"choices": [{"message": {"content": "ok"}}]},
    )


def test_to_messages_parses_nested_export():
    export = json.dumps([
        {
            "mapping": {
                "node1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Hello world"]},
                    }
                },
                "node2": {
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Hi", "there"]},
                    }
                },
            }
        }
    ])
    result = openai.to_messages(export)
    assert {"role": "user", "content": "Hello world"} in result
    assert {"role": "assistant", "content": "Hi there"} in result


def test_to_messages_skips_system_role():
    export = json.dumps([
        {
            "mapping": {
                "node1": {
                    "message": {
                        "author": {"role": "system"},
                        "content": {"parts": ["system prompt"]},
                    }
                },
            }
        }
    ])
    result = openai.to_messages(export)
    assert len(result) == 0


def test_to_messages_handles_empty_export():
    result = openai.to_messages("[]")
    assert result == []


def assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
