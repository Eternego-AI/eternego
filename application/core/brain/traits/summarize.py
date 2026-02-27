"""Summarize — condense execution results into a concise record."""

from application.core.brain.data import Trait


class _Summarize(Trait):
    name = "summarize"
    requires_permission = False
    description = (
        "Condenses the results of a completed execution cycle into a concise record. "
        "Used internally after all steps have run or when execution is interrupted."
    )
    instruction = (
        "Trait: summarize\n"
        "Summarize execution results into a concise record.\n"
        'Params: {"text": "the execution results to summarize"}'
    )

    def execution(self, text=""):
        async def _run(persona):
            from application.core.brain import ego
            from application.platform import logger
            logger.info("summarize: condensing text", {"persona_id": persona.id})
            if not text:
                return ""
            response = await ego.reason(
                persona,
                f"{text}\n\nReturn JSON: {{\"summary\": \"...\"}}",
            )
            return response.get("summary", "") if isinstance(response, dict) else ""
        return _run


trait = _Summarize()
