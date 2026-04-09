import json

import application.platform.anthropic as anthropic
from application.platform.processes import on_separate_process_async


async def test_chat_sends_correct_model_and_messages():
    def isolated():
        from application.platform import anthropic

        def run(url):
             anthropic.chat(url, "test-key", "claude-3", [{"role": "user", "content": "hi"}])

        def validate(r):
            assert r["body"]["model"] == "claude-3", r["body"]["model"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]["messages"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": "Hello"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_headers():
    def isolated():
        from application.platform import anthropic

        def run(url):
            anthropic.chat(url, "my-secret-key", "claude-3", [])

        def validate(r):
            assert r["headers"]["X-Api-Key"] == "my-secret-key", r["headers"]
            assert r["headers"]["Anthropic-Version"] == "2023-06-01", r["headers"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_returns_response_text():
    def isolated():
        from application.platform import anthropic

        result = {}
        def run(url):
            result["text"] = anthropic.chat(url, "key", "model", [])

        anthropic.assert_chat(
            run=run,
            response={"content": [{"text": "Hello from Claude"}]},
        )
        assert result["text"] == "Hello from Claude", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_returns_parsed_json():
    def isolated():
        from application.platform import anthropic

        result = {}
        def run(url):
            result["data"] = anthropic.chat_json(url, "key", "model", [])

        anthropic.assert_chat_json(
            run=run,
            response={"content": [{"text": '{"answer": 42}'}]},
        )
        assert result["data"] == {"answer": 42}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_returns_empty_on_invalid():
    def isolated():
        from application.platform import anthropic

        result = {}
        def run(url):
            result["data"] = anthropic.chat_json(url, "key", "model", [])

        anthropic.assert_chat_json(
            run=run,
            response={"content": [{"text": "not json"}]},
        )
        assert result["data"] == {}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_hits_correct_path():
    def isolated():
        from application.platform import anthropic

        def run(url):
            anthropic.chat(url, "key", "model", [])

        def validate(r):
            assert r["path"] == "/v1/messages", r["path"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_extracts_system_message():
    def isolated():
        from application.platform import anthropic

        def run(url):
            anthropic.chat(url, "key", "model", [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "hi"},
            ])

        def validate(r):
            assert r["body"]["system"] == "You are helpful", r["body"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]["messages"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_joins_multiple_system_messages():
    def isolated():
        from application.platform import anthropic

        def run(url):
            anthropic.chat(url, "key", "model", [
                {"role": "system", "content": "First."},
                {"role": "system", "content": "Second."},
                {"role": "user", "content": "hi"},
            ])

        def validate(r):
            assert r["body"]["system"] == "First.\nSecond.", r["body"]
            assert len(r["body"]["messages"]) == 1, r["body"]["messages"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_omits_system_key_when_no_system_messages():
    def isolated():
        from application.platform import anthropic

        def run(url):
            anthropic.chat(url, "key", "model", [
                {"role": "user", "content": "hi"},
            ])

        def validate(r):
            assert "system" not in r["body"], r["body"]

        anthropic.assert_chat(
            run=run,
            validate=validate,
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
