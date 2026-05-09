"""Worker — async serial executor tests.

Covers the lifecycle: idle nudge starts a tick, mid-tick nudge cancels and
re-runs, multiple nudges coalesce, stop is clean, error handling.
"""

import asyncio

from application.platform.asyncio_worker import Worker


async def test_nudge_while_idle_starts_a_tick():
    """nudge with no active tick creates a fresh tick task."""
    runs = 0
    finished = asyncio.Event()

    async def tick():
        nonlocal runs
        runs += 1
        finished.set()

    worker = Worker()
    worker._tick_fn = tick  # bind without running
    assert worker.idle, "worker should start idle"

    worker.nudge()
    await asyncio.wait_for(finished.wait(), timeout=2)
    await worker.settle(timeout=2)

    assert runs == 1
    assert worker.idle


async def test_nudge_during_tick_cancels_and_restarts():
    """When a tick is mid-run and a job inside it is cancellable, nudge
    cancels the job AND ensures the tick re-runs once it unwinds — so the
    new signal that triggered the nudge gets a fresh perception."""
    runs = 0
    first_started = asyncio.Event()
    second_started = asyncio.Event()
    worker = Worker()

    async def cognitive_work():
        await asyncio.sleep(60)  # long; will be cancelled

    async def tick():
        nonlocal runs
        runs += 1
        if runs == 1:
            first_started.set()
            await worker.dispatch(cognitive_work)
        else:
            second_started.set()

    worker.run(tick)
    await asyncio.wait_for(first_started.wait(), timeout=2)
    # Yield to let dispatch register the job before we nudge.
    await asyncio.sleep(0.01)

    worker.nudge()
    await asyncio.wait_for(second_started.wait(), timeout=2)
    await worker.settle(timeout=2)

    assert runs == 2, f"expected one restart, got runs={runs}"
    assert not worker.pending_restart, "flag should be cleared after restart"
    assert worker.idle


async def test_multiple_nudges_during_tick_collapse_to_one_restart():
    """Several nudges during a single tick all set the same flag; only one
    restart fires after the tick exits. (The flag is cleared at the top of
    the next iteration, so further mid-run nudges would queue another.)"""
    runs = 0
    first_started = asyncio.Event()
    second_started = asyncio.Event()
    worker = Worker()

    async def cognitive_work():
        await asyncio.sleep(60)

    async def tick():
        nonlocal runs
        runs += 1
        if runs == 1:
            first_started.set()
            await worker.dispatch(cognitive_work)
        else:
            second_started.set()

    worker.run(tick)
    await asyncio.wait_for(first_started.wait(), timeout=2)
    await asyncio.sleep(0.01)

    # Three nudges in quick succession.
    worker.nudge()
    worker.nudge()
    worker.nudge()

    await asyncio.wait_for(second_started.wait(), timeout=2)
    await worker.settle(timeout=2)

    # Only one restart, not three.
    assert runs == 2, f"multiple nudges should collapse, got runs={runs}"


async def test_nudge_after_stop_is_a_no_op():
    """Once stopped, nudge should not start or restart anything."""
    runs = 0

    async def tick():
        nonlocal runs
        runs += 1

    worker = Worker()
    worker._tick_fn = tick
    await worker.stop()

    worker.nudge()
    await asyncio.sleep(0.05)

    assert runs == 0
    assert worker.stopped


async def test_pending_restart_flag_is_cleared_at_loop_start():
    """Each iteration of `_loop` starts with `_pending_restart = False`.
    A nudge that fires *before* the loop runs (e.g., during stop) should
    not cause an infinite loop."""
    runs = 0
    finished = asyncio.Event()
    worker = Worker()

    async def tick():
        nonlocal runs
        runs += 1
        finished.set()

    # Pre-set pending_restart, then run.
    worker._tick_fn = tick
    worker._pending_restart = True
    worker._tick_task = asyncio.create_task(worker._loop())

    await asyncio.wait_for(finished.wait(), timeout=2)
    await worker.settle(timeout=2)

    # Tick ran exactly once — the flag was cleared at top, no restart needed
    # because nothing called nudge during the run.
    assert runs == 1
    assert not worker.pending_restart


async def test_dispatch_returns_none_when_cancelled():
    """dispatch swallows CancelledError and returns None — the contract clock
    relies on to break out of the consequences loop."""
    worker = Worker()
    worker._tick_fn = lambda: None  # so nudge doesn't fail

    async def slow():
        await asyncio.sleep(60)

    async def runner():
        return await worker.dispatch(slow)

    task = asyncio.create_task(runner())
    await asyncio.sleep(0.01)
    worker.cancel()
    result = await asyncio.wait_for(task, timeout=2)

    assert result is None
