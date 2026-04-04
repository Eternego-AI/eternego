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


def test_direct_message_is_returned():
    updates = [{"update_id": 100, "message": {"text": "hello", "chat": {"id": 123, "type": "private"}, "message_id": 1}}]
    result = telegram.direct_or_mentioned_in_group("bot", updates)
    assert result == [("hello", "123", "1")]


def test_empty_text_is_skipped():
    updates = [{"update_id": 100, "message": {"text": "", "chat": {"id": 123, "type": "private"}, "message_id": 1}}]
    assert telegram.direct_or_mentioned_in_group("bot", updates) == []


def test_missing_chat_id_is_skipped():
    updates = [{"update_id": 100, "message": {"text": "hi", "chat": {}, "message_id": 1}}]
    assert telegram.direct_or_mentioned_in_group("bot", updates) == []


def test_group_without_mention_is_skipped():
    updates = [{"update_id": 100, "message": {"text": "hello everyone", "chat": {"id": 123, "type": "group"}, "message_id": 1}}]
    assert telegram.direct_or_mentioned_in_group("eternego_bot", updates) == []


def test_group_with_mention_is_returned():
    updates = [{"update_id": 100, "message": {"text": "hey @eternego_bot help", "chat": {"id": 123, "type": "group"}, "message_id": 1}}]
    assert telegram.direct_or_mentioned_in_group("eternego_bot", updates) == [("hey @eternego_bot help", "123", "1")]


def test_multiple_updates_processed():
    updates = [
        {"update_id": 100, "message": {"text": "first", "chat": {"id": 1, "type": "private"}, "message_id": 1}},
        {"update_id": 101, "message": {"text": "second", "chat": {"id": 2, "type": "private"}, "message_id": 2}},
    ]
    assert len(telegram.direct_or_mentioned_in_group("bot", updates)) == 2


def test_empty_updates_returns_empty():
    assert telegram.direct_or_mentioned_in_group("bot", []) == []


# ── Isolated tests (swap BASE_URL) ──────────────────────────────────────────

async def test_send_posts_to_correct_url():
    def isolated():
        from application.platform import telegram
        result = {}
        def validate(r):
            assert r["path"] == "/botfake-token/sendMessage", r["path"]
            assert r["body"] == {"chat_id": "12345", "text": "Hello!"}, r["body"]
        telegram.assert_send(
            run=lambda: result.update(response=telegram.send("fake-token", "12345", "Hello!")),
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
        telegram.assert_get_me(
            run=lambda: result.update(response=telegram.get_me("fake-token")),
            validate=lambda r: None if r["path"] == "/botfake-token/getMe" else (_ for _ in ()).throw(AssertionError(r["path"])),
            response={"ok": True, "result": {"username": "test_bot"}},
        )
        assert result["response"]["result"]["username"] == "test_bot", result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_typing_action_sends_correct_payload():
    def isolated():
        from application.platform import telegram
        def validate(r):
            assert r["body"] == {"chat_id": "12345", "action": "typing"}, r["body"]
        telegram.assert_typing_action(
            run=lambda: telegram.typing_action("fake-token", "12345"),
            validate=validate,
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_poll_returns_updates_and_next_offset():
    def isolated():
        from application.platform import telegram
        def run():
            updates, offset = telegram.poll("fake-token")
            assert len(updates) == 1, f"Expected 1 update, got {len(updates)}"
            assert offset == 101, f"Expected offset 101, got {offset}"
        telegram.assert_call(
            run=run,
            response={"result": [{"update_id": 100, "message": {"text": "hi", "chat": {"id": 1}, "message_id": 1}}]},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_poll_sends_to_correct_path():
    def isolated():
        from application.platform import telegram
        def validate(r):
            assert r["path"] == "/botmy-token/getUpdates", r["path"]
        telegram.assert_call(
            run=lambda: telegram.poll("my-token"),
            validate=validate,
            response={"result": []},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_poll_sends_offset_in_request():
    def isolated():
        from application.platform import telegram
        def validate(r):
            assert r["body"]["offset"] == 42, r["body"]
        telegram.assert_call(
            run=lambda: telegram.poll("token", offset=42),
            validate=validate,
            response={"result": []},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


