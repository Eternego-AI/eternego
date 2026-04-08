from application.platform.processes import on_separate_process_async


async def test_telegram_succeeds_with_valid_token():
    def isolated():
        import os
        import tempfile
        from application.business import environment
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        result = {}

        def run():
            import asyncio
            result["value"] = asyncio.run(environment.check_channel("telegram", {"token": "fake-token"}))

        telegram.assert_get_me(
            run=run,
            response={"ok": True, "result": {"id": 123, "first_name": "Bot"}},
        )
        assert result["value"].success is True
        assert result["value"].data["type"] == "telegram"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_telegram_fails_with_invalid_token():
    def isolated():
        import os
        import json
        import tempfile
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.business import environment
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "description": "Unauthorized"}).encode())
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = telegram.BASE_URL
        telegram.BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"

        try:
            import asyncio
            result = asyncio.run(environment.check_channel("telegram", {"token": "bad-token"}))
            assert result.success is False
        finally:
            telegram.BASE_URL = original
            server.shutdown()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_unsupported_channel_type_fails():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import environment

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        result = asyncio.run(environment.check_channel("discord", {}))
        assert result.success is False
        assert "not supported" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_web_channel_type_fails():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import environment

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        result = asyncio.run(environment.check_channel("web", {}))
        assert result.success is False
        assert "not supported" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
