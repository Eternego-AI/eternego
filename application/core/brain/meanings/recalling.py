"""Meaning — recalling."""

from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Looking back at past conversations or scheduled events"

    def path(self) -> str:
        return (
            "Look back. Past conversations are held by day (`abilities.recall_history` with "
            "`date` as YYYY-MM-DD). Scheduled events live on the calendar "
            "(`abilities.check_calendar` with `date` as YYYY-MM-DD or YYYY-MM). Resolve the "
            "date from the conversation and the current time, then look it up. If the date is "
            "unclear, ask with `say` first. When the TOOL_RESULT comes back on the next cycle, "
            "reply with what you found."
        )
