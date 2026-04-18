from application.platform import telegram
from application.platform.processes import on_separate_process_async


# ── Pure tests (no globals) ─────────────────────────────────────────────────

def test_is_mentioned_with_at_prefix():
    assert telegram.is_mentioned("eternego_bot", "Hey @eternego_bot help me")


def test_is_mentioned_without_at_prefix():
    assert telegram.is_mentioned("eternego_bot", "Hey eternego_bot help me")


def test_is_mentioned_case_insensitive():
    assert telegram.is_mentioned("Eternego_Bot", "hey @eternego_bot")
    assert telegram.is_mentioned("eternego_bot", "Hey @ETERNEGO_BOT")


def test_is_mentioned_returns_false_when_absent():
    assert not telegram.is_mentioned("eternego_bot", "Hello everyone")


def test_direct_or_mentioned_filter_passes_direct():
    filter_fn = telegram.direct_or_mentioned("bot")
    assert filter_fn("hello", "private") is True


def test_direct_or_mentioned_filter_passes_group_mention():
    filter_fn = telegram.direct_or_mentioned("eternego_bot")
    assert filter_fn("hey @eternego_bot help", "group") is True


def test_direct_or_mentioned_filter_rejects_group_without_mention():
    filter_fn = telegram.direct_or_mentioned("eternego_bot")
    assert filter_fn("hello everyone", "group") is False


def test_has_command_detects_command():
    message = {"text": "/stop", "entities": [{"type": "bot_command", "offset": 0, "length": 5}]}
    assert telegram.has_command(message) == "stop"


def test_has_command_strips_bot_mention():
    message = {"text": "/stop@mybot", "entities": [{"type": "bot_command", "offset": 0, "length": 11}]}
    assert telegram.has_command(message) == "stop"


def test_has_command_returns_none_for_regular_message():
    message = {"text": "hello", "entities": []}
    assert telegram.has_command(message) is None


def test_has_command_returns_none_when_no_entities():
    message = {"text": "hello"}
    assert telegram.has_command(message) is None


# ── Isolated tests (swap BASE_URL) ──────────────────────────────────────────

async def test_send_posts_to_correct_url():
    def isolated():
        from application.platform import telegram

        result = {}
        def run():
            result["response"] = telegram.send("fake-token", "12345", "Hello!")

        def validate(r):
            assert r["path"] == "/botfake-token/sendMessage", r["path"]
            assert r["body"] == {"chat_id": "12345", "text": "Hello!"}, r["body"]

        telegram.assert_send(
            run=run,
            validate=validate,
            response={"ok": True},
        )
        assert result["response"] == {"ok": True}, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_me_calls_correct_endpoint():
    def isolated():
        from application.platform import telegram

        result = {}
        def run():
            result["response"] = telegram.get_me("fake-token")

        def validate(r):
            assert r["path"] == "/botfake-token/getMe", r["path"]

        telegram.assert_get_me(
            run=run,
            validate=validate,
            response={"ok": True, "result": {"username": "test_bot"}},
        )
        assert result["response"]["result"]["username"] == "test_bot", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_typing_action_sends_correct_payload():
    def isolated():
        from application.platform import telegram

        def run():
            telegram.typing_action("fake-token", "12345")

        def validate(r):
            assert r["body"] == {"chat_id": "12345", "action": "typing"}, r["body"]

        telegram.assert_typing_action(
            run=run,
            validate=validate,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_poll_sends_to_correct_path():
    def isolated():
        from application.platform import telegram

        def run():
            telegram.poll("my-token", 0, {})
        def validate(r):
            assert r["path"] == "/botmy-token/getUpdates", r["path"]

        telegram.assert_call(
            run=run,
            validate=validate,
            response={"result": []},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_poll_sends_offset_in_request():
    def isolated():
        from application.platform import telegram

        def run():
            telegram.poll("token", 42, {})

        def validate(r):
            assert r["body"]["offset"] == 42, r["body"]

        telegram.assert_call(
            run=run,
            validate=validate,
            response={"result": []},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


