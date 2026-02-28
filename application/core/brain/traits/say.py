"""Say — send a message to the person through a named channel."""

from application.core.brain.data import Trait


class _Say(Trait):
    name = "say"
    requires_permission = False
    description = (
        "Sends a message to the person through a specific channel. "
        "Use when you need to communicate information, answer a question, "
        "or deliver any response to the person."
    )
    instruction = (
        "Trait: say\n"
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
                return f"failed: channel '{channel_name}' not found"
            await channels.send(channel, text)
            return f"message has been sent through channel {channel_name}"
        return _run


trait = _Say()
