"""Schedule — create a scheduled event at a specific datetime."""

from application.core.brain.data import Tool


class _Schedule(Tool):
    name = "schedule"
    requires_permission = False
    description = (
        "Creates a scheduled event at a specific date and time. "
        "Use when the person wants to record an event, appointment, or task at a specific moment."
    )
    instruction = (
        "Tool: schedule\n"
        "Schedule an event at a specific datetime.\n"
        'Params: {"trigger": "YYYY-MM-DD HH:MM", "content": "event description"}'
    )

    def execution(self, trigger="", content=""):
        async def _run(persona):
            import secrets
            from datetime import datetime
            from application.core import paths
            from application.platform import logger
            logger.debug("schedule: saving event", {"persona_id": persona.id, "trigger": trigger, "content": content[:80]})
            if not trigger:
                return "no trigger provided — use clarify to ask when this should happen"
            try:
                datetime.strptime(trigger, "%Y-%m-%d %H:%M")
            except ValueError:
                return f"invalid trigger format '{trigger}' — must be YYYY-MM-DD HH:MM"
            if not content:
                return "no content provided — use clarify to ask what this event is about"
            paths.save_destiny_entry(persona.id, "schedule", trigger, secrets.token_hex(4), content)
            return f"scheduled: {trigger} — {content}"
        return _run


tool = _Schedule()
