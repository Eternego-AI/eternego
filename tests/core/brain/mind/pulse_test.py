from application.core.brain.mind.pulse import Pulse
from application.platform.asyncio_worker import Worker


def test_log_success_records_event():
    p = Pulse(Worker())
    p.log_success("realize")
    assert len(p.events) == 1
    assert p.events[0].kind == "success"
    assert p.events[0].function == "realize"
    assert p.events[0].loop == 0


def test_log_fault_records_model_details():
    p = Pulse(Worker())
    p.log_fault(
        function="recognize",
        provider="anthropic",
        url="https://api.anthropic.com",
        model_name="claude-sonnet-4-6",
        error="HTTP 429",
    )
    assert len(p.events) == 1
    e = p.events[0]
    assert e.kind == "fault"
    assert e.function == "recognize"
    assert e.provider == "anthropic"
    assert e.url == "https://api.anthropic.com"
    assert e.model_name == "claude-sonnet-4-6"
    assert e.error == "HTTP 429"


def test_next_loop_bumps_counter_and_events_record_loop_number():
    p = Pulse(Worker())
    assert p.loop_number == 0
    p.next_loop()
    assert p.loop_number == 1
    p.log_success("realize")
    p.next_loop()
    p.log_fault(function="recognize", provider="anthropic")
    assert p.events[0].loop == 1
    assert p.events[1].loop == 2


def test_clear_events_empties_log_but_keeps_loop_counter():
    p = Pulse(Worker())
    p.next_loop()
    p.log_success("realize")
    p.clear_events()
    assert p.events == []
    assert p.loop_number == 1


def test_events_are_ring_buffered():
    p = Pulse(Worker())
    for i in range(250):
        p.log_success(f"step_{i}")
    assert len(p.events) == 200
    assert p.events[-1].function == "step_249"
    assert p.events[0].function == "step_50"


def test_events_property_returns_copy():
    p = Pulse(Worker())
    p.log_success("realize")
    snapshot = p.events
    p.log_success("recognize")
    assert len(snapshot) == 1
    assert len(p.events) == 2
