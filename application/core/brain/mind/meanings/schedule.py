"""Schedule — the person wants to schedule an appointment, meeting, or event."""

import uuid

from application.core.brain.data import Meaning, Signal
from application.core import paths
from application.platform import datetimes, logger


class Scheduler(Meaning):
    name = "Scheduler"

    def description(self) -> str:
        return "The person wants to schedule an appointment, meeting, or event at a specific time."

    def clarify(self) -> str:
        return (
            "The previous attempt to schedule the event failed. "
            "Look at the error in the conversation — it could be a missing field, "
            "an invalid date format, or a timezone issue. "
            "Tell the person what went wrong in plain language and ask them "
            "to confirm or correct the details."
        )

    def reply(self) -> str:
        return "Acknowledge briefly that you will schedule it. Do not state the time or details — just confirm you are on it."

    def summarize(self) -> str:
        return (
            "The event has been scheduled. Confirm briefly — state when it is "
            "and what it is about. Mention how many upcoming events are scheduled, "
            "only counting ones that have not yet passed based on the current time."
        )

    def path(self) -> str | None:
        return (
            "Extract the event details from what the person said (ignore assistant messages).\n"
            'Return JSON: {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone from person identity", "content": "event description", "recurrence": "daily|weekly|monthly|hourly or empty string"}\n'
            "Use the person's timezone from their identity. "
            "Set recurrence only if the person explicitly asks for a recurring event. "
            "Use empty strings for any missing or inapplicable fields."
        )

    async def run(self, persona_response: dict):
        trigger = persona_response.get("trigger", "")
        timezone = persona_response.get("timezone", "")
        content = persona_response.get("content", "")
        recurrence = persona_response.get("recurrence", "")

        if not trigger or not timezone or not content:
            logger.info("schedule.run: incomplete data", {"trigger": trigger, "timezone": timezone})
            return Signal(id=str(uuid.uuid4()), role="user", content="Error: trigger, timezone, or content is missing. Extract all three from the conversation and try again.")

        try:
            utc = datetimes.to_utc(trigger, timezone)
        except Exception as e:
            logger.error("schedule.run: invalid trigger or timezone", {"error": str(e)})
            return Signal(id=str(uuid.uuid4()), role="user", content=f"Error: invalid trigger or timezone — {e}. Correct the format and try again.")

        body = content
        if recurrence:
            body += f"\nrecurrence: {recurrence}\ntimezone: {timezone}"

        paths.save_destiny_entry(
            self.persona.id,
            "schedule",
            utc.strftime("%Y-%m-%d %H:%M"),
            body,
        )
        return None
