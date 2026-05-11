from application.platform import xai
from application.platform.processes import on_separate_process_async


async def test_chat_yields_response_text():
    def isolated():
        from application.platform import xai

        result = {}
        async def consume(url):
            parts = []
            async for chunk in xai.chat(url, "key", "grok-4.3", [{"role": "user", "content": "hi"}]):
                parts.append(chunk)
            result["text"] = "".join(parts)

        xai.assert_chat(
            run=lambda url: consume(url),
            response={"choices": [{"message": {"content": "Hello from Grok"}}]},
        )
        assert result["text"] == "Hello from Grok", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_headers():
    def isolated():
        from application.platform import xai

        async def consume(url):
            async for _ in xai.chat(url, "test-key", "grok-4.3", []):
                pass

        def validate(r):
            assert r["headers"]["Authorization"] == "Bearer test-key", r["headers"]

        xai.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_hits_correct_path():
    def isolated():
        from application.platform import xai

        async def consume(url):
            async for _ in xai.chat(url, "key", "grok-4.3", []):
                pass

        def validate(r):
            assert r["path"] == "/v1/chat/completions", r["path"]

        xai.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_omits_stream_options():
    """xAI's gateway silently drops large streamed requests when stream_options
    is set — chat() must NOT include it in the body. This is the whole reason
    xai.py exists as a separate module from openai.py."""
    def isolated():
        from application.platform import xai

        async def consume(url):
            async for _ in xai.chat(url, "key", "grok-4.3", [{"role": "user", "content": "hi"}]):
                pass

        def validate(r):
            assert "stream_options" not in r["body"], r["body"]
            assert r["body"]["stream"] is True, r["body"]

        xai.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_passes_messages_through():
    def isolated():
        from application.platform import xai

        async def consume(url):
            async for _ in xai.chat(url, "key", "grok-4.3", [
                {"role": "system", "content": "Be honest"},
                {"role": "user", "content": "hi"},
            ]):
                pass

        def validate(r):
            assert r["body"]["messages"] == [
                {"role": "system", "content": "Be honest"},
                {"role": "user", "content": "hi"},
            ], r["body"]["messages"]

        xai.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": "ok"}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_sends_response_format():
    def isolated():
        from application.platform import xai

        async def consume(url):
            async for _ in xai.tool(url, "key", "grok-4.3", [{"role": "user", "content": "json"}]):
                pass

        def validate(r):
            assert r["body"]["response_format"] == {"type": "json_object"}, r["body"]

        xai.assert_tool(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_omits_stream_options():
    def isolated():
        from application.platform import xai

        async def consume(url):
            async for _ in xai.tool(url, "key", "grok-4.3", [{"role": "user", "content": "json"}]):
                pass

        def validate(r):
            assert "stream_options" not in r["body"], r["body"]

        xai.assert_tool(
            run=lambda url: consume(url),
            validate=validate,
            response={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_yields_response_text():
    def isolated():
        from application.platform import xai

        result = {}
        async def consume(url):
            parts = []
            async for chunk in xai.tool(url, "key", "grok-4.3", []):
                parts.append(chunk)
            result["text"] = "".join(parts)

        xai.assert_tool(
            run=lambda url: consume(url),
            response={"choices": [{"message": {"content": '{"result": true}'}}]},
        )
        assert result["text"] == '{"result": true}', result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_raises_connection_error_on_transport_failure():
    """xAI's silent connection drops surface as httpx.RequestError. xai.chat
    re-raises as ConnectionError so the core layer's EngineConnectionError
    wrapper can pick it up cleanly."""
    def isolated():
        import asyncio
        from application.platform import xai

        async def consume():
            # Unreachable port — connect refused — httpx raises ConnectError
            async for _ in xai.chat("http://127.0.0.1:1", "key", "grok-4.3", []):
                pass

        try:
            asyncio.run(consume())
            assert False, "expected ConnectionError"
        except ConnectionError:
            pass

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
