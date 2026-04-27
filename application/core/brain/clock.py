"""Clock — the persona's sense of time. Each run, life manifests.

Clock.run loops the cognitive cycle. Each function returns a list of
capabilities (tool/ability invocations the function declared but did not
execute). Clock's inner executor runs each item, dispatches an Event for
the capability with args/status/result as payload, and persists the
call+result pair to memory.

No restart on True/False. Each beat is one full pass through the cycle.
Tool results land in memory and are picked up on the next beat's realize.

On EngineConnectionError or BrainException from any step, run logs and
exits cleanly — health_check decides what to do.
"""

from application.core import abilities, tools
from application.core.brain.signals import BrainFault, CapabilityRun
from application.core.exceptions import BrainException, EngineConnectionError
from application.platform import logger
from application.platform.observer import dispatch


async def run(living) -> None:
    logger.debug("Running")
    worker = living.pulse.worker
    memory = living.ego.memory
    persona = living.ego.persona

    async def execute(item: dict) -> None:
        if not isinstance(item, dict) or not item:
            return
        selector, args = next(iter(item.items()))
        if not isinstance(args, dict):
            args = {} if args is None else args
        if "." not in selector:
            logger.warning("clock.execute unknown selector", {"selector": selector})
            return
        namespace, name = selector.split(".", 1)
        if namespace == "tools":
            try:
                status, result = await tools.call(name, **args)
            except Exception as e:
                status, result = "error", str(e)
        elif namespace == "abilities":
            try:
                status, result = "ok", await abilities.call(persona, name, **args)
            except Exception as e:
                status, result = "error", str(e)
        else:
            logger.warning("clock.execute unknown namespace", {"selector": selector})
            return
        memory.add_tool_result(selector, args, status, result)
        dispatch(CapabilityRun(selector, {"persona": persona, "args": args, "status": status, "result": result}))

    if worker.stopped:
        return

    for name, step in living.cycle:
        try:
            consequences = await worker.dispatch(step)
        except (EngineConnectionError, BrainException) as e:
            model = e.model
            dispatch(BrainFault(name, {
                "persona": persona,
                "provider": (model.provider or "ollama") if model else None,
                "url": model.url if model else None,
                "model_name": model.name if model else None,
                "error": str(e),
            }))
            logger.warning("Run fault", {"function": name, "error": str(e)})
            return
        if worker.stopped:
            return
        if not isinstance(consequences, list):
            continue
        for item in consequences:
            await execute(item)
            if worker.stopped:
                return
