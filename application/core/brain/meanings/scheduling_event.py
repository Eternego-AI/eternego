"""Scheduling Event — the person wants to schedule an appointment, meeting, or event."""

import secrets

from application.core.brain.meanings.meaning import Meaning
from application.core.brain.data import Signal
from application.core import paths
from application.platform import datetimes, logger


class SchedulingEvent(Meaning):
    name = "Scheduling Event"

    def description(self) -> str:
        return "The person wants to schedule an appointment, meeting, or event at a specific time."

    def clarification(self) -> str:
        return (
            "If the date, time, or event details are not clear, ask for them before confirming. "
            "If the timezone is unknown, ask the person for it."
        )

    def reply(self) -> str:
        return "Confirm the event has been scheduled, stating what it is and when."

    def path(self) -> str | None:
        return (
            "Extract the event details from this conversation.\n"
            'Return JSON: {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone, e.g. Europe/Berlin", "content": "event description"}\n'
            "Use empty strings for any missing fields."
        )

    async def run(self, persona_response: dict):
        trigger = persona_response.get("trigger", "")
        timezone = persona_response.get("timezone", "")
        content = persona_response.get("content", "")

        if not trigger or not timezone or not content:
            logger.info("scheduling_event.run: incomplete data", {"trigger": trigger, "timezone": timezone})
            return Signal(role="user", content="Error: trigger, timezone, or content is missing. Extract all three from the conversation and try again.")

        try:
            utc = datetimes.to_utc(trigger, timezone)
        except Exception as e:
            logger.error("scheduling_event.run: invalid trigger or timezone", {"error": str(e)})
            return Signal(role="user", content=f"Error: invalid trigger or timezone — {e}. Correct the format and try again.")

        paths.save_destiny_entry(
            self.persona.id,
            "schedule",
            utc.strftime("%Y-%m-%d %H:%M"),
            secrets.token_hex(4),
            content,
        )
        return None
