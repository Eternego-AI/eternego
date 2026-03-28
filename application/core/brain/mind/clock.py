"""Clock — the persona's sense of time. Using each tick, life manifests."""

from application.platform import logger
from application.core.brain.mind import conscious


async def tick(mind, worker) -> None:
    """Run the conscious pipeline until the mind has nothing left to process.

    Each step is dispatched through the worker. If a new signal arrives
    mid-step, the worker cancels the job and changed() restarts the
    pipeline from realize.

    Pipeline: realize → understand → recognize → decide → conclude
    """
    logger.debug("Ticking in mind", {"persona": mind.persona})

    pipeline = [
        conscious.realize,
        conscious.understand,
        conscious.recognize,
        conscious.decide,
        conscious.conclude,
    ]

    while not mind.settled:
        if worker.stopped:
            return
        for step in pipeline:
            await worker.dispatch(step, mind)
            if worker.stopped:
                return
            if mind.changed():
                break
