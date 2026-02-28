"""Say — send a message to the person through a named channel."""

from application.core.brain.data import Tool


class _Say(Tool):
    name = "say"
    requires_permission = False
    description = (
        "Sends a message to the person through a specific channel. "
        "Use when you need to communicate information, answer a question, "
        "or deliver any response to the person."
    )
    instruction = (
        "Tool: say\n"
        "Send a message to the person through a channel.\n"
        'Params: {"text": "message to send", "channel_name": "name of the channel"}'
    )

    def execution(self, text="", channel_name=""):
        async def _run(persona):
            from application.core import channels, gateways
            from application.platform import logger
            logger.debug("say: delivering message", {"persona_id": persona.id, "channel": channel_name, "text": text[:80]})
            channel = next(
                (c for c in gateways.of(persona).all_channels() if c.name == channel_name),
                None,
            )
            logger.debug("say: channel lookup", {"channel_name": channel_name, "found": channel is not None, "available": [c.name for c in gateways.of(persona).all_channels()]})
            if channel is None:
                channel = channels.default_channel(persona)
                if channel is None:
                    return "failed: no active channels found"
                logger.debug("say: falling back to default channel", {"channel_name": channel.name})
            await channels.send(channel, text)
            return f"message has been sent through channel {channel.name}"
        return _run


tool = _Say()
