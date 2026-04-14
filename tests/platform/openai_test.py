import json

from application.platform import openai
from application.platform.processes import on_separate_process_async


async def test_chat_yields_response_text():
    def isolated():
        import asyncio
        from application.platform import openai

        result = {}
        async def consume(url):
            parts = []
            async for chunk in openai.chat(url, "key", "gpt-4", [{"role": "user", "content": "hi"}]):
                parts.append(chunk)
            result["text"] = "".join(parts)

        openai.assert_chat(
            run=lambda url: consume(url),
            response={"choices": [{"message": {"content": "Hello from GPT"}}]},
        )
        assert result["text"] == "Hello from GPT", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_headers():
    def isolated():
        from application.platform import openai

        async def consume(url):
            async for _ in openai.chat(url, "test-key", "gpt-4", []):
                pass

        def validate(r):
            assert r["headers"]["Authorization"] == "Bearer test-key", r["headers"]

        openai.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_hits_correct_path():
    def isolated():
        from application.platform import openai

        async def consume(url):
            async for _ in openai.chat(url, "key", "gpt-4", []):
                pass

        def validate(r):
            assert r["path"] == "/v1/chat/completions", r["path"]

        openai.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_passes_system_messages_in_messages():
    def isolated():
        from application.platform import openai

        async def consume(url):
            async for _ in openai.chat(url, "key", "gpt-4", [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "hi"},
            ]):
                pass

        def validate(r):
            assert r["body"]["messages"] == [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "hi"},
            ], r["body"]["messages"]

        openai.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_sends_response_format():
    def isolated():
        from application.platform import openai

        async def consume(url):
            async for _ in openai.chat_json(url, "key", "gpt-4", [{"role": "user", "content": "json"}]):
                pass

        def validate(r):
            assert r["body"]["response_format"] == {"type": "json_object"}, r["body"]

        openai.assert_chat_json(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_yields_response_text():
    def isolated():
        import asyncio
        from application.platform import openai

        result = {}
        async def consume(url):
            parts = []
            async for chunk in openai.chat_json(url, "key", "gpt-4", []):
                parts.append(chunk)
            result["text"] = "".join(parts)

        openai.assert_chat_json(
            run=lambda url: consume(url),
            response={"choices": [{"message": {"content": '{"result": true}'}}]},
        )
        assert result["text"] == '{"result": true}', result
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
    assert len(result) == 1
    assert {"role": "user", "content": "Hello world"} in result[0]
    assert {"role": "assistant", "content": "Hi there"} in result[0]


def test_to_messages_skips_system_role():
    export = json.dumps([
        {"mapping": {"node1": {"message": {"author": {"role": "system"}, "content": {"parts": ["prompt"]}}}}}
    ])
    result = openai.to_messages(export)
    assert len(result) == 0


def test_to_messages_handles_empty_export():
    result = openai.to_messages("[]")
    assert result == []
