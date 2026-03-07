"""Reflect — interrupt the current cycle and inject a reflection to seed the next tick."""

from application.core.brain.data import Tool


class _Reflect(Tool):
    name = "reflect"
    requires_permission = False
    description = (
        "Interrupts the current cycle and injects a reflection signal to seed the next tick. "
        "Use when you have intermediate results and need a fresh cycle to continue with full context."
    )
    instruction = (
        "Tool: reflect\n"
        "Interrupt and inject a reflection to seed the next tick.\n"
        'Params: {"text": "what you observed and what should happen next"}'
    )

    def execution(self, text=""):
        async def _run(persona):
            from application.core.brain import mind
            from application.core.data import Prompt
            from application.platform import logger
            logger.debug("reflect: interrupting cycle", {"persona_id": persona.id, "text": text[:80]})
            if not text:
                return "no reflection provided"
            m = mind.get(persona.id)
            if m is None:
                return "mind not loaded"
            m.interrupt(Prompt(role="user", content=text))
            return "reflected"
        return _run


tool = _Reflect()
