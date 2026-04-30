"""Clock — the persona's sense of time. Each run, life manifests.

Clock.run loops the cognitive cycle until it settles. A pass that emits no
capabilities is settled — the persona has either spoken, said done, or had
nothing to do. A pass that runs at least one capability re-loops, so the
TOOL_RESULT just written to memory gets read by the next pass's realize and
the persona can act on what came back.

Per-pass state — `memory.impression`, `memory.ability`, `memory.meaning` —
is reset at the top of every iteration. Recognize/learn/decide are free to
set it within a pass for the internal handoff (recognize → learn → decide);
nothing carries across passes by design.

Each function returns a list of capabilities (tool/ability invocations the
function declared but did not execute). Clock's inner executor runs each
item, persists the call+result pair to memory via add_tool_result, and
dispatches a CapabilityRun event.

On EngineConnectionError or BrainException from any step, run dispatches a
BrainFault and exits. Health_check decides what to do.
"""

from application.core import abilities, tools
from application.core.brain.signals import BrainFault, CapabilityRun
from application.core.data import Media
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
        media = None
        if namespace == "tools":
            try:
                status, result = await tools.call(name, **args)
            except Exception as e:
                status, result = "error", str(e)
        elif namespace == "abilities":
            try:
                ability_result = await abilities.call(persona, name, **args)
                status = "ok"
                if isinstance(ability_result, Media):
                    media = ability_result
                    result = ability_result.caption
                else:
                    result = ability_result
            except Exception as e:
                status, result = "error", str(e)
        else:
            logger.warning("clock.execute unknown namespace", {"selector": selector})
            return
        memory.add_tool_result(selector, args, status, result, media=media)
        dispatch(CapabilityRun(selector, {"persona": persona, "args": args, "status": status, "result": result}))

    if worker.stopped:
        return

    while True:
        memory.impression = ""
        memory.ability = 0
        memory.meaning = None
        executed_any = False

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
                executed_any = True
                if worker.stopped:
                    return

        if not executed_any:
            return
