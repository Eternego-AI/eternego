import json

from application.platform import anthropic
from application.platform.processes import on_separate_process_async


async def test_chat_sends_correct_model_and_messages():
    def isolated():
        from application.platform import anthropic
        def validate(r):
            assert r["body"]["model"] == "claude-3", r["body"]["model"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]["messages"]
        anthropic.assert_chat(
            run=lambda: anthropic.chat("test-key", "claude-3", [{"role": "user", "content": "hi"}]),
            validate=validate,
            response={"content": [{"text": "Hello"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_headers():
    def isolated():
        from application.platform import anthropic
        def validate(r):
            assert r["headers"]["X-Api-Key"] == "my-secret-key", r["headers"]
            assert r["headers"]["Anthropic-Version"] == "2023-06-01", r["headers"]
        anthropic.assert_chat(
            run=lambda: anthropic.chat("my-secret-key", "claude-3", []),
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_returns_response_text():
    def isolated():
        from application.platform import anthropic
        result = {}
        anthropic.assert_chat(
            run=lambda: result.update(text=anthropic.chat("key", "model", [])),
            response={"content": [{"text": "Hello from Claude"}]},
        )
        assert result["text"] == "Hello from Claude", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_returns_parsed_json():
    def isolated():
        from application.platform import anthropic
        result = {}
        anthropic.assert_chat_json(
            run=lambda: result.update(data=anthropic.chat_json("key", "model", [])),
            response={"content": [{"text": '{"answer": 42}'}]},
        )
        assert result["data"] == {"answer": 42}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_returns_empty_on_invalid():
    def isolated():
        from application.platform import anthropic
        result = {}
        anthropic.assert_chat_json(
            run=lambda: result.update(data=anthropic.chat_json("key", "model", [])),
            response={"content": [{"text": "not json"}]},
        )
        assert result["data"] == {}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_hits_correct_path():
    def isolated():
        from application.platform import anthropic
        anthropic.assert_chat(
            run=lambda: anthropic.chat("key", "model", []),
            validate=lambda r: None if r["path"] == "/v1/messages" else (_ for _ in ()).throw(AssertionError(r["path"])),
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


def test_to_messages_parses_export():
    export = json.dumps([
        {"chat_messages": [
            {"sender": "human", "text": "Hello"},
            {"sender": "assistant", "text": "Hi there"},
        ]}
    ])
    result = anthropic.to_messages(export)
    assert result == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]


def test_to_messages_skips_system_messages():
    export = json.dumps([
        {"chat_messages": [
            {"sender": "system", "text": "You are helpful"},
            {"sender": "human", "text": "Hi"},
        ]}
    ])
    result = anthropic.to_messages(export)
    assert len(result) == 1
    assert result[0]["role"] == "user"


def test_to_messages_handles_empty_export():
    result = anthropic.to_messages("[]")
    assert result == []
