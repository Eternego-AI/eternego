import json

from application.platform import anthropic


def test_chat_sends_correct_model_and_messages():
    anthropic.assert_chat(
        run=lambda: anthropic.chat("test-key", "claude-3", [{"role": "user", "content": "hi"}]),
        validate=lambda r: (
            assert_equal(r["body"]["model"], "claude-3"),
            assert_equal(r["body"]["messages"], [{"role": "user", "content": "hi"}]),
        ),
        response={"content": [{"text": "Hello"}]},
    )


def test_chat_sends_correct_headers():
    anthropic.assert_chat(
        run=lambda: anthropic.chat("my-secret-key", "claude-3", []),
        validate=lambda r: (
            assert_equal(r["headers"]["X-Api-Key"], "my-secret-key"),
            assert_equal(r["headers"]["Anthropic-Version"], "2023-06-01"),
        ),
        response={"content": [{"text": "ok"}]},
    )


def test_chat_returns_response_text():
    result = {}
    anthropic.assert_chat(
        run=lambda: result.update(text=anthropic.chat("key", "model", [])),
        response={"content": [{"text": "Hello from Claude"}]},
    )
    assert result["text"] == "Hello from Claude"


def test_chat_json_parses_json_from_response():
    result = {}
    anthropic.assert_chat_json(
        run=lambda: result.update(data=anthropic.chat_json("key", "model", [])),
        response={"content": [{"text": '{"answer": 42}'}]},
    )
    assert result["data"] == {"answer": 42}


def test_chat_json_returns_empty_dict_on_invalid_json():
    result = {}
    anthropic.assert_chat_json(
        run=lambda: result.update(data=anthropic.chat_json("key", "model", [])),
        response={"content": [{"text": "not json at all"}]},
    )
    assert result["data"] == {}


def test_chat_hits_correct_path():
    anthropic.assert_chat(
        run=lambda: anthropic.chat("key", "model", []),
        validate=lambda r: assert_equal(r["path"], "/v1/messages"),
        response={"content": [{"text": "ok"}]},
    )


def test_to_messages_parses_export():
    export = json.dumps([
        {
            "chat_messages": [
                {"sender": "human", "text": "Hello"},
                {"sender": "assistant", "text": "Hi there"},
            ]
        }
    ])
    result = anthropic.to_messages(export)
    assert result == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]


def test_to_messages_skips_system_messages():
    export = json.dumps([
        {
            "chat_messages": [
                {"sender": "system", "text": "You are helpful"},
                {"sender": "human", "text": "Hi"},
            ]
        }
    ])
    result = anthropic.to_messages(export)
    assert len(result) == 1
    assert result[0]["role"] == "user"


def test_to_messages_handles_empty_export():
    result = anthropic.to_messages("[]")
    assert result == []


def assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
