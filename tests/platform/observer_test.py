import asyncio

from application.platform.observer import (
    Signal,
    Plan,
    Event,
    Message,
    _handlers,
    _get_signal_type,
    _matches,
    subscribe,
    send,
)


def _clear_handlers():
    _handlers.clear()


def test_signal_has_id_and_time():
    s = Signal("test", {"key": "value"})
    assert s.id
    assert s.time > 0
    assert s.title == "test"
    assert s.details == {"key": "value"}


def test_subclasses_are_distinct():
    assert not isinstance(Plan("p", {}), Event)
    assert isinstance(Plan("p", {}), Signal)
    assert isinstance(Event("e", {}), Signal)


def test_get_signal_type_extracts_from_hint():
    def handler(signal: Plan):
        pass

    assert _get_signal_type(handler) is Plan


def test_get_signal_type_returns_none_without_hint():
    def handler(signal):
        pass

    assert _get_signal_type(handler) is None


def test_matches_checks_isinstance():
    plan = Plan("p", {})
    assert _matches(plan, Plan)
    assert _matches(plan, Signal)
    assert not _matches(plan, Event)


def test_matches_handles_tuple_of_types():
    plan = Plan("p", {})
    assert _matches(plan, (Plan, Event))
    assert not _matches(plan, (Event, Message))


def test_subscribe_and_send_dispatches():
    _clear_handlers()
    received = []

    def on_plan(signal: Plan):
        received.append(signal.title)

    subscribe(on_plan)
    asyncio.run(send(Plan("hello", {})))
    assert received == ["hello"]

    # Event should not trigger Plan handler
    asyncio.run(send(Event("world", {})))
    assert received == ["hello"]
    _clear_handlers()


def test_send_dispatches_to_async_handlers():
    _clear_handlers()
    received = []

    async def on_event(signal: Event):
        received.append(signal.title)

    subscribe(on_event)
    asyncio.run(send(Event("async-test", {})))
    assert received == ["async-test"]
    _clear_handlers()
