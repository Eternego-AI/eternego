from application.platform import discord
from application.platform.observer import Event as EventSignal, Message as MessageSignal


# ── Constants ────────────────────────────────────────────────────────────────

def test_intent_constants():
    assert discord.INTENT_GUILDS == 1 << 0
    assert discord.INTENT_GUILD_MESSAGES == 1 << 9
    assert discord.INTENT_DIRECT_MESSAGES == 1 << 12
    assert discord.INTENT_MESSAGE_CONTENT == 1 << 15


# ── Connection ───────────────────────────────────────────────────────────────

def test_open_gateway():
    def validate(conn, signals):
        gateway = conn.open_gateway("test-token")
        assert gateway.token == "test-token"
        assert gateway.bot_info["username"] == "test_bot"

    received = discord.assert_call(validate=validate)
    assert received[0]["path"] == "/users/@me"
    assert received[0]["headers"]["Authorization"] == "Bot test-token"


def test_open_gateway_raises_on_invalid_token():
    def handle(method, path, body, headers):
        return (401, {"message": "401: Unauthorized"})

    def validate(conn, signals):
        try:
            conn.open_gateway("bad-token")
            assert False, "Should have raised"
        except Exception:
            pass
        assert "bad-token" not in conn._gateways

    discord.assert_call(handle=handle, validate=validate)


def test_multiple_gateways():
    def validate(conn, signals):
        conn.open_gateway("first-token")
        conn.open_gateway("second-token")
        assert len(conn._gateways) == 2

    discord.assert_call(validate=validate)


def test_close_gateway():
    def validate(conn, signals):
        gateway = conn.open_gateway("token")
        conn.close_gateway("token")
        assert "token" not in conn._gateways
        assert gateway.closed is True

    discord.assert_call(validate=validate)


def test_send():
    def validate(conn, signals):
        result = conn.request("POST", "/channels/987654321/messages", "token", {"content": "Hello!"})
        assert result["content"] == "Hello!"

    received = discord.assert_call(validate=validate)
    assert received[0]["path"] == "/channels/987654321/messages"
    assert received[0]["body"]["content"] == "Hello!"
    assert received[0]["headers"]["Authorization"] == "Bot token"


def test_async_send():
    def validate(conn, signals):
        return conn.send("token", "987654321", "Hello!")

    received = discord.assert_call(validate=validate)
    assert "/channels/987654321/messages" in received[-1]["path"]


def test_async_typing():
    def validate(conn, signals):
        return conn.typing("token", "987654321")

    received = discord.assert_call(validate=validate)
    assert "/channels/987654321/typing" in received[-1]["path"]


def test_user_agent_header():
    def validate(conn, signals):
        conn.request("GET", "/users/@me", "token")

    received = discord.assert_call(validate=validate)
    assert received[0]["headers"]["User-Agent"].startswith("DiscordBot")


# ── Gateway (WebSocket) ─────────────────────────────────────────────────────

def test_receive_text():
    def validate(conn, signals):
        conn.open_gateway("token")
        dispatched = signals()
        assert len(dispatched) == 1
        assert isinstance(dispatched[0], MessageSignal)
        assert dispatched[0].details["content"] == "hello there"
        assert dispatched[0].details["channel_id"] == "987654321"
        assert dispatched[0].details["author_id"] == "111222333"

    discord.assert_call(
        events=[{"t": "MESSAGE_CREATE", "d": {
            "id": "msg-1",
            "channel_id": "987654321",
            "content": "hello there",
            "author": {"id": "111222333", "username": "user", "bot": False},
            "attachments": [],
        }}],
        validate=validate,
    )


def test_receive_attachment():
    def validate(conn, signals):
        conn.open_gateway("token")
        dispatched = signals()
        assert len(dispatched) == 1
        assert dispatched[0].details["content"] == "check this out"
        assert dispatched[0].details["attachment_url"] == "https://cdn.discord.com/file.png"
        assert dispatched[0].details["attachment_filename"] == "file.png"

    discord.assert_call(
        events=[{"t": "MESSAGE_CREATE", "d": {
            "id": "msg-2",
            "channel_id": "987654321",
            "content": "check this out",
            "author": {"id": "111222333", "username": "user", "bot": False},
            "attachments": [{
                "url": "https://cdn.discord.com/file.png",
                "filename": "file.png",
                "content_type": "image/png",
            }],
        }}],
        validate=validate,
    )


def test_gateway_skips_bot_messages():
    def validate(conn, signals):
        conn.open_gateway("token")
        dispatched = signals(timeout=2)
        assert len(dispatched) == 1
        assert dispatched[0].details["content"] == "from human"

    discord.assert_call(
        events=[
            {"t": "MESSAGE_CREATE", "d": {
                "id": "msg-bot",
                "channel_id": "123",
                "content": "from bot",
                "author": {"id": "999", "username": "other_bot", "bot": True},
                "attachments": [],
            }},
            {"t": "MESSAGE_CREATE", "d": {
                "id": "msg-human",
                "channel_id": "123",
                "content": "from human",
                "author": {"id": "456", "username": "user", "bot": False},
                "attachments": [],
            }},
        ],
        validate=validate,
    )


def test_filter_by():
    def validate(conn, signals):
        conn.open_gateway("token", filter_by=lambda msg: msg["channel_id"] == "allowed")
        dispatched = signals()
        assert len(dispatched) == 1
        assert dispatched[0].details["content"] == "accepted"

    discord.assert_call(
        events=[
            {"t": "MESSAGE_CREATE", "d": {
                "id": "msg-1", "channel_id": "blocked", "content": "ignored",
                "author": {"id": "456", "bot": False}, "attachments": [],
            }},
            {"t": "MESSAGE_CREATE", "d": {
                "id": "msg-2", "channel_id": "allowed", "content": "accepted",
                "author": {"id": "456", "bot": False}, "attachments": [],
            }},
        ],
        validate=validate,
    )


def test_gateway_error_signals_and_exits():
    def validate(conn, signals):
        conn.gateway_url = "ws://127.0.0.1:1"
        conn.open_gateway("token")
        dispatched = signals()
        assert len(dispatched) == 1
        assert isinstance(dispatched[0], EventSignal)

    discord.assert_call(validate=validate)
