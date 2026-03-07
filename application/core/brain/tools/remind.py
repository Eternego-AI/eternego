"""Remind — set a reminder at a specific datetime."""

from application.core.brain.data import Tool


class _Remind(Tool):
    name = "remind"
    requires_permission = False
    description = (
        "Creates a new reminder at a specific date and time. "
        "Use when the person asks to be reminded of something — this sets it, it does not list existing ones."
    )
    instruction = (
        "Tool: remind\n"
        "Set a reminder at a specific datetime in the person's local time.\n"
        "If their timezone is unknown, use clarify to ask before setting the reminder.\n"
        'Params: {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone, e.g. Europe/Berlin", "content": "what to be reminded of"}'
    )

    def execution(self, trigger="", timezone="", content=""):
        async def _run(persona):
            import secrets
            from application.core import paths
            from application.platform import datetimes, logger
            logger.debug("remind: saving reminder", {"persona_id": persona.id, "trigger": trigger, "timezone": timezone, "content": content[:80]})
            if not trigger:
                return "no trigger provided — use clarify to ask when this reminder should fire"
            if not timezone:
                return "no timezone provided — use clarify to ask for the person's timezone first"
            if not content:
                return "no content provided — use clarify to ask what to be reminded about"
            try:
                utc_dt = datetimes.to_utc(trigger, timezone)
            except Exception as e:
                return f"invalid trigger or timezone: {e}"
            utc_trigger = utc_dt.strftime("%Y-%m-%d %H:%M")
            paths.save_destiny_entry(persona.id, "reminder", utc_trigger, secrets.token_hex(4), content)
            return f"reminder set: {trigger} {timezone} → {utc_trigger} UTC — {content}"
        return _run


tool = _Remind()
