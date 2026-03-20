"""Todo — notify the person about due entries and handle recurrence."""

import uuid

from application.core.brain.data import Meaning, Signal, SignalEvent
from application.core import paths
from application.platform import datetimes, logger


class Todo(Meaning):
    name = "Todo"

    def description(self) -> str:
        return "Due reminders or events that need to be communicated to the person."

    def clarify(self) -> str:
        return (
            "The previous attempt to schedule the next recurrence failed. "
            "Look at the error and try again with corrected values."
        )

    def reply(self) -> str:
        return (
            "The thread contains reminders or events that are due now. "
            "Notify the person warmly and directly about each one. "
            "If there are multiple, mention each."
        )

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        return (
            "Check the due entries in this conversation thread. "
            "For each entry that has recurrence info (e.g. 'recurrence: daily'), "
            "calculate the next trigger time in the person's timezone.\n\n"
            'Return JSON: {"next": [\n'
            '  {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone", "content": "full content with recurrence lines", "event": "reminder or schedule"}\n'
            "]}\n"
            "Only include entries that have recurrence. "
            "If no entries are recurring, return {\"next\": []}."
        )

    async def run(self, persona_response: dict):
        entries = persona_response.get("next", [])
        if not entries:
            return None

        errors = []
        for entry in entries:
            trigger = entry.get("trigger", "")
            tz = entry.get("timezone", "")
            content = entry.get("content", "")
            event = entry.get("event", "schedule")

            if not trigger or not tz or not content:
                continue

            try:
                utc = datetimes.to_utc(trigger, tz)
                paths.save_destiny_entry(
                    self.persona.id,
                    event,
                    utc.strftime("%Y-%m-%d %H:%M"),
                    content,
                )
                logger.info("todo: scheduled next recurrence", {"trigger": trigger, "event": event})
            except Exception as e:
                errors.append(f"{event} at {trigger}: {e}")

        if errors:
            return Signal(
                id=str(uuid.uuid4()), event=SignalEvent.executed,
                content=f"Error scheduling next recurrence: {'; '.join(errors)}",
            )
        return None
