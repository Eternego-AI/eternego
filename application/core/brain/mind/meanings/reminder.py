"""Reminder — the person wants to be reminded of something at a specific time."""

import secrets
import uuid

from application.core.brain.data import Meaning, Signal
from application.core import paths
from application.platform import datetimes, logger


class Reminder(Meaning):
    name = "Reminder"

    def description(self) -> str:
        return "The person wants to be reminded of something at a specific date and time."

    def clarify(self) -> str:
        return (
            "The previous attempt to set the reminder failed. "
            "Look at the error in the conversation — it could be a missing date, time, "
            "or timezone, an invalid date format, an unrecognized timezone, "
            "or a malformed response from the previous step. "
            "Tell the person what went wrong in plain language and ask them "
            "to confirm or correct the details needed."
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
            logger.info("reminder.run: incomplete data", {"trigger": trigger, "timezone": timezone})
            return Signal(id=str(uuid.uuid4()), role="user", content="Error: trigger, timezone, or content is missing. Extract all three from the conversation and try again.")

        try:
            utc = datetimes.to_utc(trigger, timezone)
        except Exception as e:
            logger.error("reminder.run: invalid trigger or timezone", {"error": str(e)})
            return Signal(id=str(uuid.uuid4()), role="user", content=f"Error: invalid trigger or timezone — {e}. Correct the format and try again.")

        paths.save_destiny_entry(
            self.persona.id,
            "reminder",
            utc.strftime("%Y-%m-%d %H:%M"),
            secrets.token_hex(4),
            content,
        )
        return None
