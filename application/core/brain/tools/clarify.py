"""Clarify — ask the person for clarification when something is uncertain."""

from application.core.brain.data import Tool


class _Clarify(Tool):
    name = "clarify"
    requires_permission = False
    description = (
        "Asks the person a clarifying question when something is uncertain or ambiguous. "
        "Use when you need more information before you can act effectively. "
        "Prefer this over say when the intent is to ask rather than inform."
    )
    instruction = (
        "Tool: clarify\n"
        "Ask the person a clarifying question when uncertain.\n"
        'Params: {"text": "clarifying question to ask", "channel_name": "name of the channel"}'
    )

    def execution(self, text="", channel_name=""):
        async def _run(persona):
            from application.core import channels, gateways
            from application.platform import logger
            logger.debug("clarify: asking for clarification", {"persona_id": persona.id, "channel": channel_name, "text": text[:80]})
            channel = next(
                (c for c in gateways.of(persona).all_channels() if c.name == channel_name),
                None,
            )
            logger.debug("clarify: channel lookup", {"channel_name": channel_name, "found": channel is not None, "available": [c.name for c in gateways.of(persona).all_channels()]})
            if channel is None:
                channel = channels.default_channel(persona)
                if channel is None:
                    return "failed: no active channels found"
                logger.debug("clarify: falling back to default channel", {"channel_name": channel.name})
            await channels.send(channel, text)
            return f"clarification requested through channel {channel.name}"
        return _run


tool = _Clarify()
