"""Reach out — deliver a message across every active channel."""

from application.core.brain.data import Tool


class _ReachOut(Tool):
    name = "reach_out"
    requires_permission = False
    description = (
        "Sends a message to all active channels simultaneously. "
        "Use when something is important enough to reach the person through every possible contact point, "
        "regardless of which channel they are currently using."
    )
    instruction = (
        "Tool: reach_out\n"
        "Send a message to every active channel at once.\n"
        'Params: {"text": "message to deliver"}'
    )

    def execution(self, text=""):
        async def _run(persona):
            from application.core import channels, gateways
            from application.platform import logger
            logger.debug("reach_out: broadcasting to all channels", {"persona_id": persona.id, "text": text[:80]})
            active = gateways.of(persona).all_channels()
            if not active:
                return "failed: no active channels found"
            sent, failed = [], []
            for channel in active:
                try:
                    await channels.send(channel, text)
                    sent.append(channel.name)
                except Exception as e:
                    failed.append(f"{channel.name} ({e})")
            parts = []
            if sent:
                parts.append(f"sent through: {', '.join(sent)}")
            if failed:
                parts.append(f"failed: {', '.join(failed)}")
            return "; ".join(parts)
        return _run


tool = _ReachOut()
