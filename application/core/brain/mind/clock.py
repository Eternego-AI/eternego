"""Clock — the persona's sense of time. Using each tick, life manifests."""

from application.core.exceptions import BrainException, EngineConnectionError
from application.platform import logger


async def tick(consciousness: list, worker) -> None:
    """Run the brain function sequence until a full pass returns True throughout.

    Each consciousness entry is a (name, callable) pair. Tick bumps the worker's
    loop counter at the top of every while iteration so health_check can see how
    many bouts of cognition happened. On EngineConnectionError or BrainException
    from any step, tick logs a fault event (attributed to the thinking or the
    faulted provider) and exits cleanly — health_check decides what to do with
    the body-level signal.
    """
    logger.debug("Ticking")

    while not worker.stopped:
        worker.next_loop()
        restart = False
        for i, (name, step) in enumerate(consciousness):
            try:
                result = await worker.dispatch(step)
            except (EngineConnectionError, BrainException) as e:
                model = e.model
                worker.log_fault(
                    function=name,
                    provider=(model.provider or "ollama") if model else None,
                    url=model.url if model else None,
                    model_name=model.name if model else None,
                    error=str(e),
                )
                logger.warning("Tick fault", {"function": name, "error": str(e)})
                return
            if worker.stopped:
                return
            worker.log_success(function=name)
            if result is not True:
                if i == 0:
                    return
                restart = True
                logger.info("Tick restarting", {"step_index": i, "result": repr(result)})
                break
        if not restart:
            return
