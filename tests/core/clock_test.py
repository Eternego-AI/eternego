import asyncio

from application.core.brain.mind.clock import tick


class FakeMemory:
    def __init__(self):
        self._settled = True
        self._changed = False

    @property
    def settled(self):
        return self._settled

    def changed(self):
        if self._changed:
            self._changed = False
            return True
        return False


class FakeWorker:
    def __init__(self):
        self.stopped = False
        self.dispatched = []

    async def dispatch(self, step):
        self.dispatched.append(step)
        await step()


async def test_tick_does_nothing_when_settled():
    memory = FakeMemory()
    worker = FakeWorker()
    await tick([], memory, worker)
    assert worker.dispatched == []


async def test_tick_runs_consciousness_steps_in_order():
    memory = FakeMemory()
    memory._settled = False
    worker = FakeWorker()
    order = []

    async def step_a():
        order.append("a")

    async def step_b():
        order.append("b")

    async def step_c():
        order.append("c")
        memory._settled = True

    await tick([step_a, step_b, step_c], memory, worker)
    assert order == ["a", "b", "c"]


async def test_tick_stops_when_worker_is_stopped():
    memory = FakeMemory()
    memory._settled = False
    worker = FakeWorker()
    order = []

    async def step_a():
        order.append("a")
        worker.stopped = True

    async def step_b():
        order.append("b")

    await tick([step_a, step_b], memory, worker)
    assert order == ["a"]


async def test_tick_restarts_consciousness_when_changed():
    memory = FakeMemory()
    memory._settled = False
    worker = FakeWorker()
    runs = []
    restart_count = 0

    async def step_a():
        nonlocal restart_count
        runs.append("a")
        if restart_count == 0:
            memory._changed = True
            restart_count += 1

    async def step_b():
        runs.append("b")
        memory._settled = True

    await tick([step_a, step_b], memory, worker)
    # First run: a → changed → restart. Second run: a → b → settled
    assert runs == ["a", "a", "b"]


async def test_tick_loops_until_settled():
    memory = FakeMemory()
    memory._settled = False
    worker = FakeWorker()
    count = 0

    async def step():
        nonlocal count
        count += 1
        if count >= 3:
            memory._settled = True

    await tick([step], memory, worker)
    assert count == 3
