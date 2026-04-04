from application.platform.processes import on_separate_process_async


async def test_signal_has_id_and_time():
    def isolated():
        from application.platform.observer import Signal

        s = Signal("test", {"key": "value"})
        assert s.id
        assert s.time > 0
        assert s.title == "test"
        assert s.details == {"key": "value"}

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_subclasses_are_distinct():
    def isolated():
        from application.platform.observer import Signal, Plan, Event

        assert not isinstance(Plan("p", {}), Event)
        assert isinstance(Plan("p", {}), Signal)
        assert isinstance(Event("e", {}), Signal)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_signal_type_extracts_from_hint():
    def isolated():
        from application.platform.observer import Plan, _get_signal_type

        def handler(signal: Plan):
            pass

        assert _get_signal_type(handler) is Plan

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_signal_type_returns_none_without_hint():
    def isolated():
        from application.platform.observer import _get_signal_type

        def handler(signal):
            pass

        assert _get_signal_type(handler) is None

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_matches_checks_isinstance():
    def isolated():
        from application.platform.observer import Signal, Plan, Event, _matches

        plan = Plan("p", {})
        assert _matches(plan, Plan)
        assert _matches(plan, Signal)
        assert not _matches(plan, Event)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_matches_handles_tuple_of_types():
    def isolated():
        from application.platform.observer import Plan, Event, Message, _matches

        plan = Plan("p", {})
        assert _matches(plan, (Plan, Event))
        assert not _matches(plan, (Event, Message))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_subscribe_and_send_dispatches():
    def isolated():
        import asyncio
        from application.platform.observer import Plan, Event, _handlers, subscribe, send

        _handlers.clear()
        received = []

        def on_plan(signal: Plan):
            received.append(signal.title)

        subscribe(on_plan)
        asyncio.run(send(Plan("hello", {})))
        assert received == ["hello"]

        asyncio.run(send(Event("world", {})))
        assert received == ["hello"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_send_dispatches_to_async_handlers():
    def isolated():
        import asyncio
        from application.platform.observer import Event, _handlers, subscribe, send

        _handlers.clear()
        received = []

        async def on_event(signal: Event):
            received.append(signal.title)

        subscribe(on_event)
        asyncio.run(send(Event("async-test", {})))
        assert received == ["async-test"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
