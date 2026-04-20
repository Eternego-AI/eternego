from application.platform.asyncio_worker import Worker


def test_log_success_records_event():
    w = Worker()
    w.log_success("realize")
    assert len(w.events) == 1
    assert w.events[0].kind == "success"
    assert w.events[0].function == "realize"
    assert w.events[0].loop == 0


def test_log_fault_records_model_details():
    w = Worker()
    w.log_fault(
        function="recognize",
        provider="anthropic",
        url="https://api.anthropic.com",
        model_name="claude-sonnet-4-6",
        error="HTTP 429",
    )
    assert len(w.events) == 1
    e = w.events[0]
    assert e.kind == "fault"
    assert e.function == "recognize"
    assert e.provider == "anthropic"
    assert e.url == "https://api.anthropic.com"
    assert e.model_name == "claude-sonnet-4-6"
    assert e.error == "HTTP 429"


def test_next_loop_bumps_counter_and_events_record_loop_number():
    w = Worker()
    assert w.loop_number == 0
    w.next_loop()
    assert w.loop_number == 1
    w.log_success("realize")
    w.next_loop()
    w.log_fault(function="recognize", provider="anthropic")
    assert w.events[0].loop == 1
    assert w.events[1].loop == 2


def test_clear_events_empties_log_but_keeps_loop_counter():
    w = Worker()
    w.next_loop()
    w.log_success("realize")
    w.clear_events()
    assert w.events == []
    assert w.loop_number == 1


def test_events_are_ring_buffered():
    w = Worker()
    for i in range(250):
        w.log_success(f"step_{i}")
    assert len(w.events) == 200
    assert w.events[-1].function == "step_249"
    assert w.events[0].function == "step_50"


def test_events_property_returns_copy():
    w = Worker()
    w.log_success("realize")
    snapshot = w.events
    w.log_success("recognize")
    assert len(snapshot) == 1
    assert len(w.events) == 2
