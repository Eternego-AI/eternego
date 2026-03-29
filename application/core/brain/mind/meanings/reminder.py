"""Reminder — the person wants to be reminded of something at a specific time."""

from application.core.brain.data import Meaning
from application.core import paths


class Reminder(Meaning):
    name = "Reminder"

    def description(self) -> str:
        return "The person asks to CREATE or SET a new reminder for a future time. This is about saving a new reminder, not about delivering one that is already due."

    def clarify(self) -> str:
        return (
            "The previous attempt to set the reminder failed. "
            "Look at the error in the conversation — it could be a missing field "
            "or an invalid date format. "
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
            'Return JSON: {"trigger": "YYYY-MM-DD HH:MM", "content": "what to be reminded of", "recurrence": "daily|weekly|monthly|hourly or empty string"}\n'
            "Set recurrence only if the person explicitly asks for a recurring reminder. "
            "Use empty strings for any missing or inapplicable fields."
        )

    async def run(self, persona_response: dict):
        trigger = persona_response.get("trigger", "")
        content = persona_response.get("content", "")
        recurrence = persona_response.get("recurrence", "")

        if not trigger or not content:
            raise ValueError("trigger or content is missing")

        body = content
        if recurrence:
            body += f"\nrecurrence: {recurrence}"

        async def action():
            paths.save_destiny_entry(self.persona.id, "reminder", trigger, body)

        return action
