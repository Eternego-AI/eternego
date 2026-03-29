"""DueNotification — notify the person about due entries and handle recurrence."""

from application.core.brain.data import Meaning
from application.core import paths
from application.platform import logger


class DueNotification(Meaning):
    name = "Due Notification"

    def description(self) -> str:
        return "A previously saved reminder or event has reached its due time and must be DELIVERED to the person now. This is a system notification, not a person asking to create something new."

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
            "calculate the next trigger time.\n\n"
            'Return JSON: {"next": [\n'
            '  {"trigger": "YYYY-MM-DD HH:MM", "content": "full content with recurrence line", "event": "reminder or schedule"}\n'
            "]}\n"
            "Only include entries that have recurrence. "
            "If no entries are recurring, return {\"next\": []}."
        )

    async def run(self, persona_response: dict):
        entries = persona_response.get("next", [])
        if not entries:
            return None

        async def action():
            errors = []
            for entry in entries:
                trigger = entry.get("trigger", "")
                content = entry.get("content", "")
                event = entry.get("event", "schedule")

                if not trigger or not content:
                    continue

                try:
                    paths.save_destiny_entry(self.persona.id, event, trigger, content)
                    logger.info("Scheduled next recurrence", {"trigger": trigger, "event": event})
                except Exception as e:
                    errors.append(f"{event} at {trigger}: {e}")

            if errors:
                return f"Error scheduling next recurrence: {'; '.join(errors)}"

        return action
