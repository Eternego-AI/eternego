import asyncio

from application.core.brain import situation
from application.core.brain.mind import clock
from application.core.brain.mind.pulse import Pulse
from application.core.data import Model
from application.core.exceptions import EngineConnectionError
from application.platform.asyncio_worker import Worker


def test_tick_logs_success_for_each_step_in_a_clean_cycle():
    async def step_true():
        return True

    async def run():
        p = Pulse(Worker())
        consciousness = [
            ("realize",   lambda: step_true()),
            ("recognize", lambda: step_true()),
            ("decide",    lambda: step_true()),
        ]
        await clock.tick(consciousness, [], p)
        return p

    p = asyncio.run(run())
    assert [e.kind for e in p.events] == ["success", "success", "success"]
    assert [e.function for e in p.events] == ["realize", "recognize", "decide"]


def test_tick_logs_fault_and_exits_on_engine_error():
    model = Model(name="qwen3:32b", url="http://localhost:11434")

    async def step_true():
        return True

    async def step_faults():
        raise EngineConnectionError("empty response", model=model)

    async def step_should_not_run():
        raise AssertionError("should not be reached")

    async def run():
        p = Pulse(Worker())
        consciousness = [
            ("realize",   lambda: step_true()),
            ("recognize", lambda: step_faults()),
            ("decide",    lambda: step_should_not_run()),
        ]
        await clock.tick(consciousness, [], p)
        return p

    p = asyncio.run(run())
    assert len(p.events) == 2
    assert p.events[0].kind == "success" and p.events[0].function == "realize"
    assert p.events[1].kind == "fault"
    assert p.events[1].function == "recognize"
    assert p.events[1].provider == "ollama"
    assert p.events[1].model_name == "qwen3:32b"
    assert p.events[1].url == "http://localhost:11434"


def test_tick_attributes_fault_to_anthropic_provider():
    model = Model(name="claude-haiku-4-5", provider="anthropic", api_key="x", url="https://api.anthropic.com")

    async def step_faults():
        raise EngineConnectionError("rate limit", model=model)

    async def run():
        p = Pulse(Worker())
        await clock.tick([("realize", lambda: step_faults())], [], p)
        return p

    p = asyncio.run(run())
    assert p.events[0].kind == "fault"
    assert p.events[0].provider == "anthropic"
    assert p.events[0].model_name == "claude-haiku-4-5"


def test_tick_increments_loop_counter_each_while_iteration():
    async def step_true():
        return True

    async def run():
        p = Pulse(Worker())
        await clock.tick([("realize", lambda: step_true())], [], p)
        return p

    p = asyncio.run(run())
    assert p.loop_number == 1


def test_tick_step_zero_false_exits_and_logs_success():
    async def step_false():
        return False

    async def step_should_not_run():
        raise AssertionError("should not be reached")

    async def run():
        p = Pulse(Worker())
        consciousness = [
            ("realize",   lambda: step_false()),
            ("recognize", lambda: step_should_not_run()),
        ]
        await clock.tick(consciousness, [], p)
        return p

    p = asyncio.run(run())
    assert len(p.events) == 1
    assert p.events[0].kind == "success"
    assert p.events[0].function == "realize"


def test_tick_exits_when_worker_is_stopped_mid_cycle():
    async def step_true():
        return True

    async def step_should_not_run():
        raise AssertionError("should not be reached")

    async def run():
        p = Pulse(Worker())

        async def step_stops_worker():
            p.worker._stopped = True
            return True

        consciousness = [
            ("realize",   lambda: step_true()),
            ("recognize", lambda: step_stops_worker()),
            ("decide",    lambda: step_should_not_run()),
        ]
        await clock.tick(consciousness, [], p)
        return p

    p = asyncio.run(run())
    assert [e.function for e in p.events] == ["realize"]


def test_tick_restarts_on_non_zero_step_returning_false():
    calls = {"realize": 0, "recognize": 0}

    async def realize():
        calls["realize"] += 1
        return True

    async def recognize():
        calls["recognize"] += 1
        return calls["recognize"] >= 2

    async def run():
        p = Pulse(Worker())
        consciousness = [
            ("realize",   lambda: realize()),
            ("recognize", lambda: recognize()),
        ]
        await clock.tick(consciousness, [], p)
        return p

    p = asyncio.run(run())
    assert calls["realize"] == 2
    assert calls["recognize"] == 2
    assert p.loop_number == 2
    assert len(p.events) == 4
    assert all(e.kind == "success" for e in p.events)


def test_tick_skips_subconscious_when_not_sleeping():
    calls = {"conscious": 0, "subconscious": 0}

    async def conscious_step():
        calls["conscious"] += 1
        return True

    async def subconscious_step():
        calls["subconscious"] += 1
        return True

    async def run():
        p = Pulse(Worker())
        conscious = [("realize", lambda: conscious_step())]
        subconscious = [("transform", lambda: subconscious_step())]
        await clock.tick(conscious, subconscious, p)
        return p

    p = asyncio.run(run())
    assert calls["conscious"] == 1
    assert calls["subconscious"] == 0
    assert p.loop_number == 1


def test_tick_runs_subconscious_when_sleeping():
    calls = {"conscious": 0, "subconscious": 0}

    async def conscious_step():
        calls["conscious"] += 1
        return True

    async def subconscious_step():
        calls["subconscious"] += 1
        return True

    async def run():
        p = Pulse(Worker())
        p.situation = situation.sleep
        conscious = [("realize", lambda: conscious_step())]
        subconscious = [("archive", lambda: subconscious_step())]
        await clock.tick(conscious, subconscious, p)
        return p

    p = asyncio.run(run())
    assert calls["conscious"] == 1
    assert calls["subconscious"] == 1


def test_tick_restarts_conscious_when_subconscious_returns_false():
    calls = {"conscious": 0, "subconscious": 0}

    async def conscious_step():
        calls["conscious"] += 1
        return True

    async def subconscious_step():
        calls["subconscious"] += 1
        return calls["subconscious"] >= 2

    async def run():
        p = Pulse(Worker())
        p.situation = situation.sleep
        conscious = [("realize", lambda: conscious_step())]
        subconscious = [("transform", lambda: subconscious_step())]
        await clock.tick(conscious, subconscious, p)
        return p

    p = asyncio.run(run())
    assert calls["conscious"] == 2
    assert calls["subconscious"] == 2
    assert p.loop_number == 2
