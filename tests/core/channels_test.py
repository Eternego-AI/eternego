import os
import asyncio
import tempfile

from application.core import channels, gateways, paths
from application.core.data import Channel, Message, Model, Persona
from application.core.exceptions import ChannelError
from application.platform import telegram


_original_home = os.environ.get("HOME")


def _setup():
    tmp = tempfile.mkdtemp()
    os.environ["HOME"] = tmp
    gateways._active.clear()


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home
    gateways._active.clear()


def _persona():
    return Persona(id="test-ch", name="Primus", model=Model(name="llama3"))


# ── verify ───────────────────────────────────────────────────────────────────

def test_verify_sets_channel_name_and_verified_at():
    _setup()
    p = _persona()
    paths.home(p.id).mkdir(parents=True, exist_ok=True)
    paths.save_as_string(paths.persona_identity(p.id), "{}")

    ch = Channel(type="telegram", name="", credentials={"token": "t"})
    p.channels = [ch]

    channels.verify(p, ch, "12345")

    assert ch.name == "12345"
    assert ch.verified_at is not None
    _teardown()


# ── send (telegram) ─────────────────────────────────────────────────────────

def test_send_telegram_sends_to_correct_chat():
    _setup()
    ch = Channel(type="telegram", name="12345", credentials={"token": "fake-token"})

    telegram.assert_send(
        run=lambda: asyncio.run(channels.send(ch, "Hello!")),
        validate=lambda r: (
            _assert_equal(r["body"]["chat_id"], "12345"),
            _assert_equal(r["body"]["text"], "Hello!"),
        ),
        response={"ok": True},
    )
    _teardown()


# ── send (web/bus) ───────────────────────────────────────────────────────────

def test_send_web_puts_to_bus():
    _setup()
    received = []

    class FakeBus:
        async def put(self, text):
            received.append(text)

    ch = Channel(type="web", name="uuid", bus=FakeBus())
    asyncio.run(channels.send(ch, "Hello from web"))

    assert received == ["Hello from web"]
    _teardown()


# ── send_all ─────────────────────────────────────────────────────────────────

def test_send_all_sends_to_all_active_channels():
    _setup()
    p = _persona()
    received = []

    class FakeBus:
        async def put(self, text):
            received.append(text)

    ch1 = Channel(type="web", name="w1", bus=FakeBus())
    ch2 = Channel(type="web", name="w2", bus=FakeBus())
    gateways.of(p).add(ch1, {"type": "manual"})
    gateways.of(p).add(ch2, {"type": "manual"})

    asyncio.run(channels.send_all(p, "broadcast"))

    assert len(received) == 2
    _teardown()


# ── express_thinking ─────────────────────────────────────────────────────────

def test_express_thinking_sends_typing_to_telegram_channels():
    _setup()
    p = _persona()
    ch = Channel(type="telegram", name="12345", credentials={"token": "fake-token"})
    gateways.of(p).add(ch, {"type": "manual"})

    telegram.assert_typing_action(
        run=lambda: asyncio.run(channels.express_thinking(p)),
        validate=lambda r: _assert_equal(r["body"]["action"], "typing"),
    )
    _teardown()


def test_express_thinking_skips_non_telegram_channels():
    _setup()
    p = _persona()

    class FakeBus:
        async def put(self, text): pass

    ch = Channel(type="web", name="w1", bus=FakeBus())
    gateways.of(p).add(ch, {"type": "manual"})

    asyncio.run(channels.express_thinking(p))
    _teardown()


# ── keep_open ────────────────────────────────────────────────────────────────

def test_keep_open_returns_polling_strategy_for_telegram():
    _setup()
    p = _persona()
    ch = Channel(type="telegram", name="12345", credentials={"token": "fake-token"})

    strategy = channels.keep_open(p, ch)

    assert strategy["type"] == "polling"
    assert callable(strategy["connection"])
    _teardown()


def test_keep_open_connection_returns_messages_from_poll():
    _setup()
    p = _persona()
    ch = Channel(type="telegram", name="", credentials={"token": "fake-token"})

    strategy = channels.keep_open(p, ch)

    # Fake the poll response
    telegram.assert_call(
        run=lambda: _assert_messages(strategy["connection"](), expected_count=1),
        validate=lambda r: _assert_equal(r["path"], "/botfake-token/getUpdates"),
        response={"result": [
            {"update_id": 100, "message": {"text": "hello", "chat": {"id": 123, "type": "private"}, "message_id": 1}}
        ]},
    )
    _teardown()


def test_keep_open_connection_filters_group_without_mention():
    _setup()
    p = _persona()
    ch = Channel(type="telegram", name="", credentials={"token": "fake-token"})

    strategy = channels.keep_open(p, ch)

    telegram.assert_call(
        run=lambda: _assert_messages(strategy["connection"](), expected_count=0),
        response={"result": [
            {"update_id": 100, "message": {"text": "not for bot", "chat": {"id": 123, "type": "group"}, "message_id": 1}}
        ]},
    )
    _teardown()


def test_keep_open_raises_on_unsupported_channel():
    _setup()
    try:
        channels.keep_open(_persona(), Channel(type="unknown", name="x"))
        assert False, "should have raised"
    except ChannelError as e:
        assert "Unsupported" in str(e)
    _teardown()


def _assert_messages(messages, expected_count):
    assert len(messages) == expected_count, f"Expected {expected_count} messages, got {len(messages)}"
    for msg in messages:
        assert isinstance(msg, Message)


def _assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
