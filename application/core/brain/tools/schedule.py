"""Schedule — create a scheduled event at a specific datetime."""

from application.core.brain.data import Tool


class _Schedule(Tool):
    name = "schedule"
    requires_permission = False
    meaning_only = True
    instruction = (
        "Tool: schedule\n"
        "Schedule an event at a specific datetime in the person's local time.\n"
        "If their timezone is unknown, ask the person before scheduling.\n"
        'Params: {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone, e.g. Europe/Berlin", "content": "event description"}'
    )

    def execution(self, trigger="", timezone="", content=""):
        async def _run(persona):
            import secrets
            from application.core import paths
            from application.platform import datetimes, logger
            logger.debug("schedule: saving event", {"persona_id": persona.id, "trigger": trigger, "timezone": timezone, "content": content[:80]})
            if not trigger:
                return "no trigger provided — ask the person when this should happen"
            if not timezone:
                return "no timezone provided — ask the person for their timezone first"
            if not content:
                return "no content provided — ask the person what this event is about"
            try:
                utc_dt = datetimes.to_utc(trigger, timezone)
            except Exception as e:
                return f"invalid trigger or timezone: {e}"
            utc_trigger = utc_dt.strftime("%Y-%m-%d %H:%M")
            paths.save_destiny_entry(persona.id, "schedule", utc_trigger, secrets.token_hex(4), content)
            return f"scheduled: {trigger} {timezone} → {utc_trigger} UTC — {content}"
        return _run


tool = _Schedule()
