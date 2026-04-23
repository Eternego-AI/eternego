"""Clock — the persona's sense of time. Using each tick, life manifests."""

from application.core.brain import situation
from application.core.exceptions import BrainException, EngineConnectionError
from application.platform import logger


async def tick(conscious: list, subconscious: list, pulse) -> None:
    """Run the cognitive cycle: conscious loop until settled, then subconscious.

    Conscious entries run in sequence. If any step returns non-True, the loop
    restarts from the top (except the first step, which exits the tick — nothing
    to process). When the full conscious pass completes and the pulse's situation
    is sleep, subconscious steps run. If a subconscious step returns non-True,
    the entire tick restarts from conscious.

    On EngineConnectionError or BrainException from any step, tick logs a fault
    and exits cleanly — health_check decides what to do.
    """
    logger.debug("Ticking")
    worker = pulse.worker

    while not worker.stopped:
        pulse.next_loop()
        restart = False

        for i, (name, step) in enumerate(conscious):
            try:
                result = await worker.dispatch(step)
            except (EngineConnectionError, BrainException) as e:
                model = e.model
                pulse.log_fault(
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
            pulse.log_success(function=name)
            if result is not True:
                if i == 0:
                    return
                restart = True
                logger.info("Tick restarting", {"step": name, "result": repr(result)})
                break

        if restart:
            continue

        if pulse.situation is not situation.sleep:
            return

        for name, step in subconscious:
            try:
                result = await worker.dispatch(step)
            except (EngineConnectionError, BrainException) as e:
                model = e.model
                pulse.log_fault(
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
            pulse.log_success(function=name)
            if result is not True:
                restart = True
                logger.info("Tick restarting from subconscious", {"step": name, "result": repr(result)})
                break

        if not restart:
            return
