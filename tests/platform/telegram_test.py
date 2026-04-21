import threading
import tempfile
from application.platform import telegram
from application.platform.observer import Command as CommandSignal, Event as EventSignal, Message as MessageSignal


# ── Pure helpers ─────────────────────────────────────────────────────────────

def test_has_command_detects_command():
    message = {"text": "/stop", "entities": [{"type": "bot_command", "offset": 0, "length": 5}]}
    assert telegram.has_command(message) == "stop"


def test_has_command_strips_bot_mention():
    message = {"text": "/stop@mybot", "entities": [{"type": "bot_command", "offset": 0, "length": 11}]}
    assert telegram.has_command(message) == "stop"


def test_has_command_returns_none_for_regular_message():
    message = {"text": "hello", "entities": []}
    assert telegram.has_command(message) is None


def test_is_mentioned():
    assert telegram.is_mentioned("eternego_bot", "Hey @eternego_bot help me")
    assert not telegram.is_mentioned("eternego_bot", "Hello everyone")


def test_direct_or_mentioned():
    f = telegram.direct_or_mentioned("eternego_bot")
    assert f({"text": "hello", "caption": "", "chat_type": "private"}) is True
    assert f({"text": "hey @eternego_bot", "caption": "", "chat_type": "group"}) is True
    assert f({"text": "hello everyone", "caption": "", "chat_type": "group"}) is False
    assert f({"text": "", "caption": "@eternego_bot photo", "chat_type": "supergroup"}) is True


# ── Connection ───────────────────────────────────────────────────────────────

def test_open_gateway():
    def validate(conn, signals):
        gateway = conn.open_gateway("test-token")
        assert gateway.token == "test-token"
        assert gateway.bot_info["username"] == "test_bot"

    received = telegram.assert_call(validate=validate)
    assert received[0]["path"] == "/bottest-token/getMe"


def test_open_gateway_raises_on_invalid_token():
    def handle(path, body):
        return (401, {"ok": False, "description": "Unauthorized"})

    def validate(conn, signals):
        try:
            conn.open_gateway("bad-token")
            assert False, "Should have raised"
        except Exception:
            pass
        assert "bad-token" not in conn._gateways

    telegram.assert_call(handle=handle, validate=validate)


def test_open_gateway_sets_commands():
    def validate(conn, signals):
        conn.open_gateway("token", commands=[{"command": "stop", "description": "Stop"}])

    received = telegram.assert_call(validate=validate)
    assert any("/setMyCommands" in r["path"] for r in received)


def test_multiple_gateways():
    def validate(conn, signals):
        conn.open_gateway("first-token")
        conn.open_gateway("second-token")
        assert len(conn._gateways) == 2

    telegram.assert_call(validate=validate)


def test_close_gateway():
    def validate(conn, signals):
        gateway = conn.open_gateway("token")
        conn.close_gateway("token")
        assert "token" not in conn._gateways
        assert gateway.closed is True

    telegram.assert_call(validate=validate)


def test_send():
    def validate(conn, signals):
        result = conn.request("/bottoken/sendMessage", {"chat_id": "12345", "text": "Hello!"})
        assert result["ok"]
        assert result["result"]["text"] == "Hello!"

    received = telegram.assert_call(validate=validate)
    assert received[0]["path"] == "/bottoken/sendMessage"
    assert received[0]["body"]["chat_id"] == "12345"


def test_async_send():
    def validate(conn, signals):
        return conn.send("token", "12345", "Hello!")

    received = telegram.assert_call(validate=validate)
    assert received[0]["path"] == "/bottoken/sendMessage"


def test_async_typing():
    def validate(conn, signals):
        return conn.typing("token", "12345")

    received = telegram.assert_call(validate=validate)
    assert received[0]["path"] == "/bottoken/sendChatAction"
    assert received[0]["body"]["action"] == "typing"


# ── Polling ──────────────────────────────────────────────────────────────────

def test_receive_text():
    def validate(conn, signals):
        conn.open_gateway("token")
        dispatched = signals()
        assert len(dispatched) == 1
        assert isinstance(dispatched[0], MessageSignal)
        assert dispatched[0].details["content"] == "Hello"
        assert dispatched[0].details["chat_id"] == "1469967968"

    telegram.assert_call(
        updates=[{"update_id": 401730030, "message": {
            "message_id": 2,
            "from": {"id": 1469967968, "is_bot": False, "first_name": "Morteza"},
            "chat": {"id": 1469967968, "first_name": "Morteza", "type": "private"},
            "date": 1776771469,
            "text": "Hello",
        }}],
        validate=validate,
    )


def test_receive_command():
    def validate(conn, signals):
        conn.open_gateway("token")
        dispatched = signals()
        assert len(dispatched) == 1
        assert isinstance(dispatched[0], CommandSignal)
        assert dispatched[0].details["command"] == "start"

    telegram.assert_call(
        updates=[{"update_id": 401730029, "message": {
            "message_id": 1,
            "from": {"id": 1469967968, "is_bot": False, "first_name": "Morteza"},
            "chat": {"id": 1469967968, "first_name": "Morteza", "type": "private"},
            "date": 1776771457,
            "text": "/start",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        }}],
        validate=validate,
    )


def test_receive_image_with_caption():
    media_dir = tempfile.mkdtemp()
    image_bytes = b"\x89PNG fake image bytes"
    polls = []

    def validate(conn, signals):
        conn.open_gateway("token", media_path=media_dir)
        threading.Thread(target=polls[0], daemon=True).start()
        dispatched = signals()
        assert len(dispatched) == 1
        assert isinstance(dispatched[0], MessageSignal)
        assert dispatched[0].details["content"] == "Image with caption"
        assert dispatched[0].details["attachment_path"].endswith(".jpg")
        with open(dispatched[0].details["attachment_path"], "rb") as f:
            assert f.read() == image_bytes

    telegram.assert_call(
        updates=[{"update_id": 401730031, "message": {
            "message_id": 3,
            "from": {"id": 1469967968, "is_bot": False, "first_name": "Morteza"},
            "chat": {"id": 1469967968, "first_name": "Morteza", "type": "private"},
            "date": 1776771490,
            "photo": [
                {"file_id": "small_id", "file_unique_id": "s1", "file_size": 800, "width": 90, "height": 24},
                {"file_id": "large_id", "file_unique_id": "l1", "file_size": 10788, "width": 564, "height": 148},
            ],
            "caption": "Image with caption",
        }}],
        files={"large_id": {"path": "photos/file_0.jpg", "content": image_bytes}},
        polling=lambda fn: polls.append(fn),
        validate=validate,
    )


def test_poll_sends_correct_offset():
    def validate(conn, signals):
        conn.open_gateway("token")
        signals()

    received = telegram.assert_call(
        updates=[{"update_id": 42, "message": {
            "message_id": 1,
            "from": {"id": 123, "is_bot": False, "first_name": "User"},
            "chat": {"id": 123, "first_name": "User", "type": "private"},
            "date": 0,
            "text": "first",
        }}],
        validate=validate,
    )
    update_requests = [r for r in received if "/getUpdates" in r["path"]]
    assert update_requests[0]["body"]["offset"] == 0
    assert update_requests[1]["body"]["offset"] == 43


def test_filter_by():
    polls = []

    def validate(conn, signals):
        conn.open_gateway("token", filter_by=lambda msg: msg["chat_type"] == "private")
        threading.Thread(target=polls[0], daemon=True).start()
        dispatched = signals()
        assert len(dispatched) == 1
        assert dispatched[0].details["content"] == "accepted"

    telegram.assert_call(
        updates=[
            {"update_id": 1, "message": {
                "message_id": 1,
                "from": {"id": 100, "is_bot": False, "first_name": "User"},
                "chat": {"id": 100, "first_name": "Group", "type": "group"},
                "date": 0, "text": "ignored",
            }},
            {"update_id": 2, "message": {
                "message_id": 2,
                "from": {"id": 200, "is_bot": False, "first_name": "User"},
                "chat": {"id": 200, "first_name": "User", "type": "private"},
                "date": 0, "text": "accepted",
            }},
        ],
        polling=lambda fn: polls.append(fn),
        validate=validate,
    )


def test_direct_or_mentioned_as_filter():
    polls = []

    def validate(conn, signals):
        conn.open_gateway("token", filter_by=telegram.direct_or_mentioned("test_bot"))
        threading.Thread(target=polls[0], daemon=True).start()
        dispatched = signals()
        assert len(dispatched) == 1
        assert dispatched[0].details["content"] == "hey @test_bot help"

    telegram.assert_call(
        updates=[
            {"update_id": 1, "message": {
                "message_id": 1,
                "from": {"id": 100, "is_bot": False, "first_name": "User"},
                "chat": {"id": 100, "first_name": "Group", "type": "group"},
                "date": 0, "text": "hello everyone",
            }},
            {"update_id": 2, "message": {
                "message_id": 2,
                "from": {"id": 200, "is_bot": False, "first_name": "User"},
                "chat": {"id": 200, "first_name": "Group", "type": "group"},
                "date": 0, "text": "hey @test_bot help",
            }},
        ],
        polling=lambda fn: polls.append(fn),
        validate=validate,
    )


def test_poll_error_signals_and_exits():
    def handle(path, body):
        if "/getMe" in path:
            return {"ok": True, "result": {"id": 12345, "is_bot": True, "first_name": "TestBot", "username": "test_bot"}}
        if "/getUpdates" in path:
            return (500, {"ok": False, "description": "Internal Server Error"})
        return {"ok": True}

    def validate(conn, signals):
        conn.open_gateway("token")
        dispatched = signals()
        assert len(dispatched) == 1
        assert isinstance(dispatched[0], EventSignal)

    telegram.assert_call(
        handle=handle,
        polling=lambda fn: threading.Thread(target=fn, daemon=True).start(),
        validate=validate,
    )
