"""Reminder — the person wants to be reminded of something at a specific time."""

from application.core.brain.data import Meaning
from application.core import paths
from application.platform import datetimes


class Reminder(Meaning):
    name = "Reminder"

    def description(self) -> str:
        return "The person asks to CREATE or SET a new reminder for a future time. This is about saving a new reminder, not about delivering one that is already due."

    def clarify(self) -> str:
        return (
            "The previous attempt to set the reminder failed. "
            "Look at the error in the conversation — it could be a missing field, "
            "an invalid date format, or a timezone issue. "
            "Tell the person what went wrong in plain language and ask them "
            "to confirm or correct the details."
        )

    def reply(self) -> str:
        return "Acknowledge briefly that you will set the reminder. Do not state the time or details — just confirm you are on it."

    def summarize(self) -> str:
        return (
            "The reminder has been set. Confirm briefly — state the time and "
            "what it is about. Mention how many upcoming reminders are scheduled, "
            "only counting ones that have not yet passed based on the current time."
        )

    def path(self) -> str | None:
        return (
            "Extract the reminder details from what the person said (ignore assistant messages).\n"
            'Return JSON: {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone from person identity", "content": "what to be reminded of", "recurrence": "daily|weekly|monthly|hourly or empty string"}\n'
            "Use the person's timezone from their identity. "
            "Set recurrence only if the person explicitly asks for a recurring reminder. "
            "Use empty strings for any missing or inapplicable fields."
        )

    async def run(self, persona_response: dict):
        trigger = persona_response.get("trigger", "")
        timezone = persona_response.get("timezone", "")
        content = persona_response.get("content", "")
        recurrence = persona_response.get("recurrence", "")

        if not trigger or not timezone or not content:
            raise ValueError("trigger, timezone, or content is missing")

        utc = datetimes.to_utc(trigger, timezone)
        body = content
        if recurrence:
            body += f"\nrecurrence: {recurrence}\ntimezone: {timezone}"

        async def action():
            paths.save_destiny_entry(
                self.persona.id,
                "reminder",
                utc.strftime("%Y-%m-%d %H:%M"),
                body,
            )

        return action
