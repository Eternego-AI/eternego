"""Clock — the persona's sense of time. Using each tick, life manifests."""

from application.platform import logger


async def tick(consciousness: list, worker) -> None:
    """Run the brain function sequence until a full pass returns True throughout.

    A step must return True to let the loop advance. Anything else — False, or
    None from a cancelled dispatch when a nudge interrupts the current step —
    restarts the loop from the top. Exits when a full pass completes with every
    step returning True, or when the worker is permanently stopped.
    """
    logger.debug("Ticking")

    while not worker.stopped:
        restart = False
        for i, step in enumerate(consciousness):
            result = await worker.dispatch(step)
            if worker.stopped:
                return
            if result is not True:
                if i == 0:
                    return
                restart = True
                logger.info("Tick restarting", {"step_index": i, "result": repr(result)})
                break
        if not restart:
            return
