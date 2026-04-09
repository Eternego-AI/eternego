from application.platform.processes import on_separate_process_async


async def test_telegram_succeeds_with_valid_token():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import environment
        from application.platform import telegram

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        result = {}

        async def run():
            result["value"] = await environment.check_channel("telegram", {"token": "fake-token"})

        telegram.assert_get_me(
            run=run,
            response={"ok": True, "result": {"id": 123, "first_name": "Bot"}},
        )
        assert result["value"].success, result["value"].message
        assert result["value"].data["channel"].type == "telegram"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_telegram_fails_with_invalid_token():
    def isolated():
        from application.business import environment
        from application.platform import telegram

        async def run():
            await environment.check_channel("telegram", {"token": "bad-token"})

        telegram.assert_call(
            run=run,
            response={"ok": False, "description": "Unauthorized"},
            status_code=401,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_web_channel_succeeds():
    def isolated():
        import asyncio
        from application.business import environment

        result = asyncio.run(environment.check_channel("web", {}))
        assert result.success, result.message
        assert result.data["channel"].type == "web"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
