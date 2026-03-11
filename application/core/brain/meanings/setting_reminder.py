"""Setting Reminder — the person wants to be reminded of something at a specific time."""

import secrets

from application.core.brain.meanings.meaning import Meaning
from application.core.brain.data import Signal
from application.core import paths
from application.platform import datetimes, logger


class SettingReminder(Meaning):
    name = "Setting Reminder"

    def description(self) -> str:
        return "The person wants to be reminded of something at a specific date and time."

    def clarification(self) -> str:
        return (
            "If the exact date and time are not clear, ask for them before confirming. "
            "If the timezone is unknown, ask the person for it."
        )

    def reply(self) -> str:
        return "Confirm the reminder has been set, stating what will be reminded and when."

    def path(self) -> str | None:
        return (
            "Extract the reminder details from this conversation.\n"
            'Return JSON: {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone, e.g. Europe/Berlin", "content": "what to be reminded of"}\n'
            "Use empty strings for any missing fields."
        )

    async def run(self, persona_response: dict):
        trigger = persona_response.get("trigger", "")
        timezone = persona_response.get("timezone", "")
        content = persona_response.get("content", "")

        if not trigger or not timezone or not content:
            logger.info("setting_reminder.run: incomplete data", {"trigger": trigger, "timezone": timezone})
            return Signal(role="user", content="Error: trigger, timezone, or content is missing. Extract all three from the conversation and try again.")

        try:
            utc = datetimes.to_utc(trigger, timezone)
        except Exception as e:
            logger.error("setting_reminder.run: invalid trigger or timezone", {"error": str(e)})
            return Signal(role="user", content=f"Error: invalid trigger or timezone — {e}. Correct the format and try again.")

        paths.save_destiny_entry(
            self.persona.id,
            "reminder",
            utc.strftime("%Y-%m-%d %H:%M"),
            secrets.token_hex(4),
            content,
        )
        return None
