"""Clarify — ask the person for clarification when something is uncertain."""

from application.core.brain.data import Trait


class _Clarify(Trait):
    name = "clarify"
    requires_permission = False
    description = (
        "Asks the person a clarifying question when something is uncertain or ambiguous. "
        "Use when you need more information before you can act effectively. "
        "Prefer this over say when the intent is to ask rather than inform."
    )
    instruction = (
        "Trait: clarify\n"
        "Ask the person a clarifying question when uncertain.\n"
        'Params: {"text": "clarifying question to ask", "channel_name": "name of the channel"}'
    )

    def execution(self, text="", channel_name=""):
        async def _run(persona):
            from application.core import channels, gateways
            from application.platform import logger
            logger.info("clarify: asking for clarification", {"persona_id": persona.id, "channel": channel_name})
            channel = next(
                (c for c in gateways.of(persona).all_channels() if c.name == channel_name),
                None,
            )
            if channel is None:
                return f"failed: channel '{channel_name}' not found"
            await channels.send(channel, text)
            return f"clarification requested through channel {channel_name}"
        return _run


trait = _Clarify()
