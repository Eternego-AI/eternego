import asyncio

from application.core.brain.mind.clock import tick


class FakeWorker:
    def __init__(self):
        self.stopped = False

    async def dispatch(self, step):
        if self.stopped:
            return None
        return await step()


async def test_tick_stops_when_first_step_returns_false():
    worker = FakeWorker()
    order = []

    async def realize():
        order.append("realize")
        return False

    async def recognize():
        order.append("recognize")
        return True

    await tick([realize, recognize], worker)
    assert order == ["realize"]


async def test_tick_runs_all_steps_in_order():
    worker = FakeWorker()
    order = []

    async def step_a():
        order.append("a")
        return True

    async def step_b():
        order.append("b")
        return True

    async def step_c():
        order.append("c")
        return True

    await tick([step_a, step_b, step_c], worker)
    assert order == ["a", "b", "c"]


async def test_tick_stops_when_worker_is_stopped():
    worker = FakeWorker()
    order = []

    async def step_a():
        order.append("a")
        worker.stopped = True
        return True

    async def step_b():
        order.append("b")
        return True

    await tick([step_a, step_b], worker)
    assert order == ["a"]


async def test_tick_restarts_when_non_first_step_returns_false():
    worker = FakeWorker()
    runs = []
    restart_count = 0

    async def realize():
        runs.append("realize")
        return True

    async def decide():
        nonlocal restart_count
        runs.append("decide")
        if restart_count == 0:
            restart_count += 1
            return False
        return True

    await tick([realize, decide], worker)
    assert runs == ["realize", "decide", "realize", "decide"]


async def test_tick_exits_after_full_true_pass():
    worker = FakeWorker()
    count = 0

    async def step():
        nonlocal count
        count += 1
        return True

    await tick([step], worker)
    assert count == 1
