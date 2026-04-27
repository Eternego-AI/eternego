"""Meaning — scheduling."""

from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Saving a reminder or event for a future moment, or responding when one has come due"

    def path(self) -> str:
        return (
            "Hold time-bound things. Two situations call for this meaning.\n\n"
            "**The person asks you to save something for a future moment.** Resolve the trigger "
            "time from the conversation and the current time. A `reminder` is a personal nudge; "
            "a `schedule` is an appointment at a fixed time. If the essentials are missing "
            "(what, when), ask with `say` first. Use `abilities.save_destiny` with `type`, "
            "`trigger` (YYYY-MM-DD HH:MM), `content`, and optionally `recurrence` (daily, weekly, "
            "monthly, hourly).\n\n"
            "**A `due for:` message has arrived.** A saved item has come due right now. Notify "
            "the person with what is due, when, and any urgency — use `notify` so it reaches "
            "them on every channel at once. If the due item's body contains a `recurrence:` "
            "line, call `abilities.save_destiny` for the next occurrence in the next cycle so "
            "the chain continues."
        )
