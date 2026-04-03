"""Clock — the persona's sense of time. Using each tick, life manifests."""

from application.platform import logger


async def tick(consciousness: list, memory, worker) -> None:
    """Run the consciousness sequence until the mind has nothing left to process.

    Each step is dispatched through the worker. If a new signal arrives
    mid-step, the worker cancels the job and changed() restarts the
    sequence from the beginning.
    """
    logger.debug("Ticking")

    while not memory.settled:
        if worker.stopped:
            return
        for step in consciousness:
            await worker.dispatch(step)
            if worker.stopped:
                return
            if memory.changed():
                break
