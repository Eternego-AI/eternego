"""Escalate — consult a more capable frontier model when the local model is not confident."""

from application.core.brain.data import Trait


class _Escalate(Trait):
    name = "escalate"
    requires_permission = False
    description = (
        "Consults a more capable frontier model for questions or tasks that exceed local confidence. "
        "Use when the question is complex, requires specialised knowledge, or when uncertain about the answer."
    )
    instruction = (
        "Trait: escalate\n"
        "Consult a more capable model when the question exceeds local confidence.\n"
        'Params: {"question": "the question or task to escalate"}'
    )

    def execution(self, question=""):
        async def _run(persona):
            from application.core import frontier
            from application.platform import logger
            logger.info("escalate: consulting frontier model", {"persona_id": persona.id})
            if not persona.frontier:
                return (
                    "No frontier model is configured. "
                    "Acknowledge the uncertainty honestly and let the person know a more capable model would help."
                )
            return await frontier.chat(persona.frontier, question)
        return _run


trait = _Escalate()
