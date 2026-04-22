"""Meaning — setting a reminder or scheduling an event."""

from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Setting a reminder or scheduling an event"

    def prompt(self) -> str:
        return (
            "Save a reminder or schedule an event. `reminder` is personal — a nudge for the person. "
            "`schedule` is an appointment at a fixed time. Resolve the trigger time from the "
            "conversation and the Current Time. If `what` or `when` is missing, ask with `say` first.\n\n"
            "## Tools\n\n"
            "- `save_destiny(type, trigger, content, recurrence?)`\n"
            "  - `type`: `reminder` or `schedule`.\n"
            "  - `trigger`: `YYYY-MM-DD HH:MM`.\n"
            "  - `content`: what to remind or describe.\n"
            "  - `recurrence` (optional): `daily`, `weekly`, `monthly`, `hourly`, or `\"\"`.\n"
            "- `say(text)` — message the person.\n\n"
            "## Output\n\n"
            "Saving and confirming:\n"
            "```json\n"
            '{"tool": "save_destiny", "type": "<reminder|schedule>",\n'
            ' "trigger": "<YYYY-MM-DD HH:MM>", "content": "<what>", "recurrence": "<see above>",\n'
            ' "say": "<confirmation>"}\n'
            "```\n\n"
            "Asking for clarification:\n"
            "```json\n"
            '{"tool": "say", "text": "<question>"}\n'
            "```"
        )
