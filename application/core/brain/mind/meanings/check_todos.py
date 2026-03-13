"""CheckTodos — periodic check of reminders, scheduled events, and routines."""

from application.core.brain.data import Meaning


class CheckTodos(Meaning):
    name = "Check Todos"

    def description(self) -> str:
        return (
            "Time to check today's schedule, reminders, and routines. "
            "Look at the current situation for what is due."
        )

    def clarify(self) -> str | None:
        return None

    def reply(self) -> str:
        return (
            "Check today's schedule from the current situation. "
            "If any reminders or events are due now or overdue, notify the person warmly and directly. "
            "If a routine like sleep is due, let the person know it is time. "
            "If nothing is due right now, say nothing — do not respond."
        )

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        return None
