import asyncio

from application.core.brain.mind import clock
from application.core.data import Model
from application.core.exceptions import EngineConnectionError
from application.platform.asyncio_worker import Worker


def test_tick_logs_success_for_each_step_in_a_clean_cycle():
    async def step_true():
        return True

    async def run():
        w = Worker()
        consciousness = [
            ("realize",   lambda: step_true()),
            ("recognize", lambda: step_true()),
            ("decide",    lambda: step_true()),
        ]
        await clock.tick(consciousness, w)
        return w

    w = asyncio.run(run())
    assert [e.kind for e in w.events] == ["success", "success", "success"]
    assert [e.function for e in w.events] == ["realize", "recognize", "decide"]


def test_tick_logs_fault_and_exits_on_engine_error():
    model = Model(name="qwen3:32b", url="http://localhost:11434")

    async def step_true():
        return True

    async def step_faults():
        raise EngineConnectionError("empty response", model=model)

    async def step_should_not_run():
        raise AssertionError("should not be reached")

    async def run():
        w = Worker()
        consciousness = [
            ("realize",   lambda: step_true()),
            ("recognize", lambda: step_faults()),
            ("decide",    lambda: step_should_not_run()),
        ]
        await clock.tick(consciousness, w)
        return w

    w = asyncio.run(run())
    assert len(w.events) == 2
    assert w.events[0].kind == "success" and w.events[0].function == "realize"
    assert w.events[1].kind == "fault"
    assert w.events[1].function == "recognize"
    assert w.events[1].provider == "ollama"
    assert w.events[1].model_name == "qwen3:32b"
    assert w.events[1].url == "http://localhost:11434"


def test_tick_attributes_fault_to_anthropic_provider():
    model = Model(name="claude-haiku-4-5", provider="anthropic", api_key="x", url="https://api.anthropic.com")

    async def step_faults():
        raise EngineConnectionError("rate limit", model=model)

    async def run():
        w = Worker()
        await clock.tick([("realize", lambda: step_faults())], w)
        return w

    w = asyncio.run(run())
    assert w.events[0].kind == "fault"
    assert w.events[0].provider == "anthropic"
    assert w.events[0].model_name == "claude-haiku-4-5"


def test_tick_increments_loop_counter_each_while_iteration():
    async def step_true():
        return True

    # Single-step consciousness that returns True → while exits after 1 iteration
    async def run():
        w = Worker()
        await clock.tick([("realize", lambda: step_true())], w)
        return w

    w = asyncio.run(run())
    assert w.loop_number == 1


def test_tick_step_zero_false_exits_and_logs_success():
    async def step_false():
        return False

    async def step_should_not_run():
        raise AssertionError("should not be reached")

    async def run():
        w = Worker()
        consciousness = [
            ("realize",   lambda: step_false()),
            ("recognize", lambda: step_should_not_run()),
        ]
        await clock.tick(consciousness, w)
        return w

    w = asyncio.run(run())
    assert len(w.events) == 1
    assert w.events[0].kind == "success"
    assert w.events[0].function == "realize"


def test_tick_exits_when_worker_is_stopped_mid_cycle():
    async def step_true():
        return True

    async def step_should_not_run():
        raise AssertionError("should not be reached")

    async def run():
        w = Worker()

        async def step_stops_worker():
            w._stopped = True
            return True

        consciousness = [
            ("realize",   lambda: step_true()),
            ("recognize", lambda: step_stops_worker()),
            ("decide",    lambda: step_should_not_run()),
        ]
        await clock.tick(consciousness, w)
        return w

    w = asyncio.run(run())
    # recognize stopped the worker mid-cycle; tick exits after dispatch without
    # logging success for an aborted step. decide is never reached.
    assert [e.function for e in w.events] == ["realize"]


def test_tick_restarts_on_non_zero_step_returning_false():
    calls = {"realize": 0, "recognize": 0}

    async def realize():
        calls["realize"] += 1
        return True

    async def recognize():
        calls["recognize"] += 1
        # First call returns False (triggers restart), second returns True (ends loop)
        return calls["recognize"] >= 2

    async def run():
        w = Worker()
        consciousness = [
            ("realize",   lambda: realize()),
            ("recognize", lambda: recognize()),
        ]
        await clock.tick(consciousness, w)
        return w

    w = asyncio.run(run())
    assert calls["realize"] == 2       # restarted once
    assert calls["recognize"] == 2
    assert w.loop_number == 2          # two while iterations
    # 4 success events: realize, recognize, realize, recognize
    assert len(w.events) == 4
    assert all(e.kind == "success" for e in w.events)
