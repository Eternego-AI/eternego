"""Clarify — ask the person for clarification when something is uncertain."""

from application.core.brain.data import Tool


class _Clarify(Tool):
    name = "clarify"
    internal = True  # hidden from focus selection; the model uses it via the clarify skill
    requires_permission = False
    description = (
        "Asks the person a clarifying question when something is uncertain or ambiguous."
    )
    instruction = (
        "Tool: clarify\n"
        "Ask the person a clarifying question when uncertain.\n"
        'Params: {"text": "clarifying question to ask"}'
    )

    def execution(self, text="", **_):
        async def _run(persona):
            from application.core import channels
            from application.platform import logger
            logger.debug("clarify: asking for clarification", {"persona_id": persona.id, "text": text[:80]})
            channel = channels.latest(persona) or channels.default_channel(persona)
            if channel is None:
                return "failed: no active channels found"
            await channels.send(channel, text)
            return f"asked: {text}"
        return _run


tool = _Clarify()
