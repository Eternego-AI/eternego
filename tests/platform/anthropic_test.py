import json

import application.platform.anthropic as anthropic
from application.platform.processes import on_separate_process_async


async def test_chat_yields_response_text():
    def isolated():
        import asyncio
        from application.platform import anthropic

        result = {}
        async def consume(url):
            parts = []
            async for chunk in anthropic.chat(url, "key", "model", [{"role": "user", "content": "hi"}]):
                parts.append(chunk)
            result["text"] = "".join(parts)

        anthropic.assert_chat(
            run=lambda url: consume(url),
            response={"content": [{"text": "Hello from Claude"}]},
        )
        assert result["text"] == "Hello from Claude", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_headers():
    def isolated():
        from application.platform import anthropic

        async def consume(url):
            async for _ in anthropic.chat(url, "my-secret-key", "claude-3", []):
                pass

        def validate(r):
            assert r["headers"]["x-api-key"] == "my-secret-key", r["headers"]
            assert r["headers"]["anthropic-version"] == "2023-06-01", r["headers"]

        anthropic.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_hits_correct_path():
    def isolated():
        from application.platform import anthropic

        async def consume(url):
            async for _ in anthropic.chat(url, "key", "model", []):
                pass

        def validate(r):
            assert r["path"] == "/v1/messages", r["path"]

        anthropic.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_extracts_system_message():
    def isolated():
        from application.platform import anthropic

        async def consume(url):
            async for _ in anthropic.chat(url, "key", "model", [
                {"role": "system", "content": "You are helpful", "cache_control": "ephemeral"},
                {"role": "user", "content": "hi"},
            ]):
                pass

        def validate(r):
            assert r["body"]["system"] == [
                {"type": "text", "text": "You are helpful", "cache_control": {"type": "ephemeral", "ttl": "1h"}},
            ], r["body"]
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}], r["body"]["messages"]
            assert r["headers"].get("anthropic-beta") == "extended-cache-ttl-2025-04-11", r["headers"]

        anthropic.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_joins_multiple_system_messages():
    def isolated():
        from application.platform import anthropic

        async def consume(url):
            async for _ in anthropic.chat(url, "key", "model", [
                {"role": "system", "content": "First.", "cache_control": "ephemeral"},
                {"role": "system", "content": "Second."},
                {"role": "user", "content": "hi"},
            ]):
                pass

        def validate(r):
            assert r["body"]["system"] == [
                {"type": "text", "text": "First.\nSecond.", "cache_control": {"type": "ephemeral", "ttl": "1h"}},
            ], r["body"]
            assert r["headers"].get("anthropic-beta") == "extended-cache-ttl-2025-04-11", r["headers"]

        anthropic.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_omits_system_key_when_no_system_messages():
    def isolated():
        from application.platform import anthropic

        async def consume(url):
            async for _ in anthropic.chat(url, "key", "model", [{"role": "user", "content": "hi"}]):
                pass

        def validate(r):
            assert "system" not in r["body"], r["body"]
            assert "anthropic-beta" not in r["headers"], r["headers"]

        anthropic.assert_chat(
            run=lambda url: consume(url),
            validate=validate,
            response={"content": [{"text": "ok"}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_does_not_mutate_caller_content_list():
    """List content is the persona's stored Memory.Message.prompt.content
    by reference. The cache_control attached for caching must not bleed
    back into the source — successive ticks would otherwise stack
    cache_control blocks until Anthropic rejects the request."""
    def isolated():
        from application.platform import anthropic

        original_block = {"type": "text", "text": "hi"}
        original_content = [original_block]

        async def consume(url):
            async for _ in anthropic.chat(url, "key", "model", [
                {"role": "user", "content": original_content, "cache_control": "ephemeral"},
            ]):
                pass

        anthropic.assert_chat(
            run=lambda url: consume(url),
            response={"content": [{"text": "ok"}]},
        )

        assert "cache_control" not in original_block, original_block
        assert original_content == [{"type": "text", "text": "hi"}], original_content
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_always_sends_tool_use_body():
    """tool() always uses tool_use mode — body carries a permissive `act`
    tool and forces it via `tool_choice`. There is no chat fallback."""
    def isolated():
        from application.platform import anthropic

        async def consume(url):
            async for _ in anthropic.tool(url, "key", "model", [{"role": "user", "content": "hi"}]):
                pass

        def validate(r):
            assert r["body"]["tools"] == [{"name": "act", "input_schema": {"type": "object", "minProperties": 1}}], r["body"]
            assert r["body"]["tool_choice"] == {"type": "tool", "name": "act"}, r["body"]

        anthropic.assert_tool(
            run=lambda url: consume(url),
            validate=validate,
            response={"tool_use_input": '{"say": "hello"}'},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_falls_back_to_content_block_start_input():
    """When the model commits to an empty/small tool input upfront,
    Anthropic ships it in `content_block_start.input` and emits empty
    `input_json_delta` heartbeats. tool() yields the start-event input
    so callers parse a valid JSON object rather than getting an empty stream."""
    def isolated():
        import asyncio, json, threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.platform import anthropic

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = self.headers.get("Content-Length")
                if content_length:
                    self.rfile.read(int(content_length))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                start = {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "tool_use", "id": "toolu_1", "name": "act", "input": {}},
                }
                self.wfile.write(f"data: {json.dumps(start)}\n\n".encode())
                heartbeat = {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": ""}}
                self.wfile.write(f"data: {json.dumps(heartbeat)}\n\n".encode())
                block_stop = {"type": "content_block_stop", "index": 0}
                self.wfile.write(f"data: {json.dumps(block_stop)}\n\n".encode())
                msg_stop = {"type": "message_stop"}
                self.wfile.write(f"data: {json.dumps(msg_stop)}\n\n".encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            async def consume():
                parts = []
                async for chunk in anthropic.tool(url, "key", "model", [{"role": "user", "content": "hi"}]):
                    parts.append(chunk)
                return "".join(parts)
            result = asyncio.run(consume())
            assert result == "{}", repr(result)
        finally:
            server.shutdown()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_yields_input_json_chunks():
    """input_json_delta events yield their partial_json as chunks; the
    concatenation is the tool's argument JSON."""
    def isolated():
        from application.platform import anthropic

        result = {}
        async def consume(url):
            parts = []
            async for chunk in anthropic.tool(url, "key", "model", [{"role": "user", "content": "hi"}]):
                parts.append(chunk)
            result["text"] = "".join(parts)

        anthropic.assert_tool(
            run=lambda url: consume(url),
            response={"tool_use_input": '{"done": null}'},
        )
        assert result["text"] == '{"done": null}', result
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
    assert result == [[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]]


def test_to_messages_skips_system_messages():
    export = json.dumps([
        {"chat_messages": [
            {"sender": "system", "text": "You are helpful"},
            {"sender": "human", "text": "Hi"},
        ]}
    ])
    result = anthropic.to_messages(export)
    assert len(result) == 1
    assert result[0][0]["role"] == "user"


def test_to_messages_handles_empty_export():
    result = anthropic.to_messages("[]")
    assert result == []
