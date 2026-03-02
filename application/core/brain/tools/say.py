"""Say — send a message to the person through a named channel."""

from application.core.brain.data import Tool


class _Say(Tool):
    name = "say"
    requires_permission = False
    description = (
        "Sends a message to the person. "
        "Use when you need to communicate information, answer a question, "
        "or deliver any response to the person."
    )
    instruction = (
        "Tool: say\n"
        "Send a message to the person.\n"
        'Params: {"text": "message to send"}'
    )

    def execution(self, text="", **_):
        async def _run(persona):
            from application.core import channels
            from application.platform import logger
            logger.debug("say: delivering message", {"persona_id": persona.id, "text": text[:80]})
            channel = channels.latest(persona) or channels.default_channel(persona)
            if channel is None:
                return "failed: no active channels found"
            await channels.send(channel, text)
            return f"message sent"
        return _run


tool = _Say()
