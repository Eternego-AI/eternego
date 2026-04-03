import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from application.platform import telegram


def test_is_mentioned_with_at_prefix():
    assert telegram.is_mentioned("eternego_bot", "Hey @eternego_bot help me")


def test_is_mentioned_without_at_prefix():
    assert telegram.is_mentioned("eternego_bot", "Hey eternego_bot help me")


def test_is_mentioned_case_insensitive():
    assert telegram.is_mentioned("Eternego_Bot", "hey @eternego_bot")
    assert telegram.is_mentioned("eternego_bot", "Hey @ETERNEGO_BOT")


def test_is_mentioned_returns_false_when_absent():
    assert not telegram.is_mentioned("eternego_bot", "Hello everyone")


def test_send_posts_message_to_correct_url():
    result = {}
    telegram.assert_send(
        run=lambda: result.update(response=telegram.send("fake-token", "12345", "Hello!")),
        validate=lambda r: (
            assert_equal(r["path"], "/botfake-token/sendMessage"),
            assert_equal(r["body"], {"chat_id": "12345", "text": "Hello!"}),
        ),
        response={"ok": True},
    )
    assert result["response"] == {"ok": True}


def test_get_me_calls_correct_endpoint():
    result = {}
    telegram.assert_get_me(
        run=lambda: result.update(response=telegram.get_me("fake-token")),
        validate=lambda r: assert_equal(r["path"], "/botfake-token/getMe"),
        response={"ok": True, "result": {"username": "test_bot"}},
    )
    assert result["response"]["result"]["username"] == "test_bot"


def test_typing_action_sends_correct_payload():
    telegram.assert_typing_action(
        run=lambda: telegram.typing_action("fake-token", "12345"),
        validate=lambda r: assert_equal(r["body"], {"chat_id": "12345", "action": "typing"}),
    )


# ── direct_or_mentioned_in_group ─────────────────────────────────────────────

def test_direct_message_is_returned():
    updates = [
        {"update_id": 100, "message": {"text": "hello", "chat": {"id": 123, "type": "private"}, "message_id": 1}}
    ]
    result = telegram.direct_or_mentioned_in_group("bot", updates)
    assert result == [("hello", "123", "1")]


def test_empty_text_is_skipped():
    updates = [
        {"update_id": 100, "message": {"text": "", "chat": {"id": 123, "type": "private"}, "message_id": 1}}
    ]
    result = telegram.direct_or_mentioned_in_group("bot", updates)
    assert result == []


def test_missing_chat_id_is_skipped():
    updates = [
        {"update_id": 100, "message": {"text": "hi", "chat": {}, "message_id": 1}}
    ]
    result = telegram.direct_or_mentioned_in_group("bot", updates)
    assert result == []


def test_group_without_mention_is_skipped():
    updates = [
        {"update_id": 100, "message": {"text": "hello everyone", "chat": {"id": 123, "type": "group"}, "message_id": 1}}
    ]
    result = telegram.direct_or_mentioned_in_group("eternego_bot", updates)
    assert result == []


def test_group_with_mention_is_returned():
    updates = [
        {"update_id": 100, "message": {"text": "hey @eternego_bot help", "chat": {"id": 123, "type": "group"}, "message_id": 1}}
    ]
    result = telegram.direct_or_mentioned_in_group("eternego_bot", updates)
    assert result == [("hey @eternego_bot help", "123", "1")]


def test_multiple_updates_processed():
    updates = [
        {"update_id": 100, "message": {"text": "first", "chat": {"id": 1, "type": "private"}, "message_id": 1}},
        {"update_id": 101, "message": {"text": "second", "chat": {"id": 2, "type": "private"}, "message_id": 2}},
    ]
    result = telegram.direct_or_mentioned_in_group("bot", updates)
    assert len(result) == 2


def test_empty_updates_returns_empty():
    result = telegram.direct_or_mentioned_in_group("bot", [])
    assert result == []


# ── poll ─────────────────────────────────────────────────────────────────────

def test_poll_returns_updates_and_next_offset():
    telegram.assert_call(
        run=lambda: _assert_poll_result(
            telegram.poll("fake-token"),
            expected_count=1,
            expected_offset=101,
        ),
        response={"result": [
            {"update_id": 100, "message": {"text": "hi", "chat": {"id": 1}, "message_id": 1}}
        ]},
    )


def test_poll_sends_to_correct_path():
    telegram.assert_call(
        run=lambda: telegram.poll("my-token"),
        validate=lambda r: assert_equal(r["path"], "/botmy-token/getUpdates"),
        response={"result": []},
    )


def test_poll_returns_same_offset_when_no_updates():
    telegram.assert_call(
        run=lambda: _assert_poll_result(
            telegram.poll("token", offset=50),
            expected_count=0,
            expected_offset=50,
        ),
        response={"result": []},
    )


def test_poll_sends_offset_in_request():
    telegram.assert_call(
        run=lambda: telegram.poll("token", offset=42),
        validate=lambda r: assert_equal(r["body"]["offset"], 42),
        response={"result": []},
    )


def _assert_poll_result(result, expected_count, expected_offset):
    updates, offset = result
    assert len(updates) == expected_count, f"Expected {expected_count} updates, got {len(updates)}"
    assert offset == expected_offset, f"Expected offset {expected_offset}, got {offset}"


def assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
