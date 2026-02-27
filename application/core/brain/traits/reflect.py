"""Reflect — interrupt the current cycle and inject a reflection to seed the next tick."""

from application.core.brain.data import Trait


class _Reflect(Trait):
    name = "reflect"
    requires_permission = False
    description = (
        "Interrupts the current cycle and injects a reflection signal to seed the next tick. "
        "Use when you have intermediate results and need a fresh cycle to continue with full context."
    )
    instruction = (
        "Trait: reflect\n"
        "Interrupt and inject a reflection to seed the next tick.\n"
        'Params: {"text": "what you observed and what should happen next"}'
    )

    def execution(self, text=""):
        async def _run(persona):
            from application.core.brain import mind as brain_mind
            from application.platform import logger
            logger.info("reflect: interrupting cycle", {"persona_id": persona.id})
            if not text:
                return "no reflection provided"
            m = brain_mind.get(persona.id)
            if m is None:
                return "mind not loaded"
            m.interrupt(text)
            return "reflected"
        return _run


trait = _Reflect()
