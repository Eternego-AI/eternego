import asyncio
import time

from application.core.gateways import of, _active
from application.core.data import Channel, Message, Persona, Model


def _persona():
    return Persona(id="test-gw", name="Primus", model=Model(name="llama3"))


def _reset():
    _active.clear()


def _strategy():
    return {"type": "manual"}


def test_add_and_all_channels():
    _reset()
    p = _persona()
    conn = of(p)
    ch = Channel(type="telegram", name="123")
    conn.add(ch, _strategy())
    assert len(conn.all_channels()) == 1
    assert conn.all_channels()[0].name == "123"
    _reset()


def test_has_channel():
    _reset()
    p = _persona()
    conn = of(p)
    ch = Channel(type="telegram", name="123")
    assert not conn.has_channel(ch)
    conn.add(ch, _strategy())
    assert conn.has_channel(ch)
    _reset()


def test_has_channel_matches_by_type_and_name():
    _reset()
    p = _persona()
    conn = of(p)
    conn.add(Channel(type="telegram", name="123"), _strategy())
    assert conn.has_channel(Channel(type="telegram", name="123"))
    assert not conn.has_channel(Channel(type="telegram", name="456"))
    assert not conn.has_channel(Channel(type="web", name="123"))
    _reset()


def test_remove_channel():
    _reset()
    p = _persona()
    conn = of(p)
    ch = Channel(type="telegram", name="123")
    conn.add(ch, _strategy())
    conn.remove(ch)
    assert len(conn.all_channels()) == 0
    _reset()


def test_clear_removes_all():
    _reset()
    p = _persona()
    conn = of(p)
    conn.add(Channel(type="telegram", name="1"), _strategy())
    conn.add(Channel(type="telegram", name="2"), _strategy())
    conn.clear()
    assert len(conn.all_channels()) == 0
    _reset()


def test_connections_are_per_persona():
    _reset()
    p1 = Persona(id="p1", name="A", model=Model(name="llama3"))
    p2 = Persona(id="p2", name="B", model=Model(name="llama3"))
    of(p1).add(Channel(type="telegram", name="1"), _strategy())
    of(p2).add(Channel(type="telegram", name="2"), _strategy())
    assert len(of(p1).all_channels()) == 1
    assert len(of(p2).all_channels()) == 1
    assert of(p1).all_channels()[0].name == "1"
    assert of(p2).all_channels()[0].name == "2"
    _reset()


def test_polling_dispatches_messages_to_on_message():
    _reset()
    received = []
    call_count = [0]

    msg = Message(channel=Channel(type="telegram", name="123"), content="hello", id="m1")

    def connection():
        call_count[0] += 1
        if call_count[0] == 1:
            return [msg]
        # Return empty after first call, sleep to avoid busy loop
        time.sleep(0.05)
        return []

    def on_message(m):
        received.append(m)

    async def run():
        p = _persona()
        ch = Channel(type="telegram", name="123")
        of(p).add(ch, {"type": "polling", "connection": connection, "on_message": on_message})

        # Give the thread time to poll and dispatch
        await asyncio.sleep(0.2)

        of(p).clear()

    asyncio.run(run())

    assert len(received) == 1
    assert received[0].content == "hello"
    _reset()


def test_polling_stops_when_channel_removed():
    _reset()
    call_count = [0]

    def connection():
        call_count[0] += 1
        time.sleep(0.05)
        return []

    async def run():
        p = _persona()
        ch = Channel(type="telegram", name="123")
        of(p).add(ch, {"type": "polling", "connection": connection, "on_message": lambda m: None})

        await asyncio.sleep(0.15)
        of(p).clear()
        count_at_clear = call_count[0]

        await asyncio.sleep(0.15)
        count_after = call_count[0]

        # Thread should have stopped — count shouldn't grow much after clear
        assert count_after - count_at_clear <= 1

    asyncio.run(run())
    _reset()


def test_polling_dispatches_async_on_message():
    _reset()
    received = []
    call_count = [0]

    msg = Message(channel=Channel(type="telegram", name="123"), content="async hello", id="m1")

    def connection():
        call_count[0] += 1
        if call_count[0] == 1:
            return [msg]
        time.sleep(0.05)
        return []

    async def on_message(m):
        received.append(m)

    async def run():
        p = _persona()
        ch = Channel(type="telegram", name="123")
        of(p).add(ch, {"type": "polling", "connection": connection, "on_message": on_message})

        # Give time for thread to poll and for coroutine to be dispatched
        await asyncio.sleep(0.3)

        of(p).clear()

    asyncio.run(run())

    assert len(received) == 1
    assert received[0].content == "async hello"
    _reset()


def test_polling_handles_connection_errors():
    _reset()
    call_count = [0]

    def connection():
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("connection failed")
        time.sleep(0.05)
        return []

    async def run():
        p = _persona()
        ch = Channel(type="telegram", name="123")
        of(p).add(ch, {"type": "polling", "connection": connection, "on_message": lambda m: None})

        await asyncio.sleep(0.2)
        of(p).clear()

    # Should not crash — error is logged and polling continues
    asyncio.run(run())
    assert call_count[0] > 1
    _reset()
