"""Clock — the persona's sense of time. Each run, life manifests.

Clock.run loops the cognitive cycle until it settles. A pass that emits no
capabilities is settled — the persona has either spoken, said done, or had
nothing to do. A pass that runs at least one capability re-loops, so the
TOOL_RESULT just written to memory gets read by the next pass's realize and
the persona can act on what came back.

Cognitive state lives in the message stream — recognize emits a
`tools.load_instruction` call (assistant message), learn writes the matching
TOOL_RESULT (user message), decide reads it. The handoff is visible to the
persona in her own conversation; nothing is mutated out-of-band.

Each function returns a list of capabilities (tool/ability invocations the
function declared but did not execute). Clock's inner executor runs each
item in order, persists the call+result pair to memory via add_tool_result,
and dispatches a CapabilityRun event. On the first non-ok status, it stops
running the remaining items — partial TOOL_RESULTs in memory become the
re-entry signal for realize on the next pass.

On EngineConnectionError or BrainException from any step, run dispatches a
BrainFault and exits. Health_check decides what to do.
"""

from application.core import abilities, tools
from application.core.brain.signals import BrainFault, CapabilityRun
from application.core.data import Media
from application.core.exceptions import BrainException, EngineConnectionError, ReflectInterrupted
from application.platform import logger
from application.platform.observer import dispatch


async def run(living) -> None:
    logger.debug("Running")
    worker = living.pulse.worker
    memory = living.memory
    persona = living.ego.persona

    async def execute(item: dict) -> str | None:
        if not isinstance(item, dict) or not item:
            return None
        selector, args = next(iter(item.items()))
        if not isinstance(args, dict):
            args = {} if args is None else args
        if "." not in selector:
            logger.warning("clock.execute unknown selector", {"selector": selector})
            return None
        namespace, name = selector.split(".", 1)
        if namespace != "tools":
            logger.warning("clock.execute unknown namespace", {"selector": selector})
            return None
        media = None
        # Persona's view: one `tools.<name>` namespace. Code's view: platform
        # primitives in `tools` registry, persona-aware verbs in `abilities`
        # registry. Look up by name; platform takes precedence on a clash.
        platform_names = {t.name for t in tools.discover()}
        ability_names = {a.name for a in abilities.available(persona)}
        if name in platform_names:
            try:
                status, result = await tools.call(name, **args)
            except Exception as e:
                status, result = "error", str(e)
        elif name in ability_names:
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
            logger.warning("clock.execute unknown tool name", {"selector": selector})
            status, result = "error", f"unknown tool: {name}"
        memory.add_tool_result(selector, args, status, result, media=media)
        dispatch(CapabilityRun(selector, {"persona": persona, "args": args, "status": status, "result": result}))
        return status

    if worker.stopped:
        return

    while True:
        executed_any = False

        try:
            for name, step in living.mind:
                try:
                    consequences = await worker.dispatch(step)
                except (EngineConnectionError, BrainException) as e:
                    model = e.model
                    details = getattr(e, "details", {}) or {}
                    dispatch(BrainFault(name, {
                        "persona": persona,
                        "provider": (model.provider or "ollama") if model else None,
                        "url": model.url if model else None,
                        "model_name": model.name if model else None,
                        "error": str(e),
                        "details": details,
                    }))
                    log_payload = {"function": name, "error": str(e)}
                    if details:
                        log_payload["details"] = details
                    logger.warning("Run fault", log_payload)
                    return
                if worker.stopped:
                    return
                if consequences is None:
                    break
                if not isinstance(consequences, list):
                    continue
                for item in consequences:
                    status = await execute(item)
                    executed_any = True
                    if worker.stopped:
                        return
                    if worker.pending_restart:
                        # A signal arrived during this consequence — let the
                        # current call land in memory, then abandon any
                        # remaining queued items. The outer break re-perceives.
                        break
                    if status is not None and status != "ok":
                        break
                if executed_any:
                    break
        except ReflectInterrupted:
            continue

        if not executed_any:
            return
