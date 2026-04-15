"""Meaning — reminders and scheduled events."""

from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"The person wants {persona.name} to set a reminder or schedule an event"


def prompt(persona: Persona) -> str:
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
        '{"reason": "<one sentence>", "tool": "save_destiny", "type": "<reminder|schedule>",\n'
        ' "trigger": "<YYYY-MM-DD HH:MM>", "content": "<what>", "recurrence": "<see above>",\n'
        ' "say": "<confirmation>"}\n'
        "```\n\n"
        "Asking for clarification:\n"
        "```json\n"
        '{"reason": "<what is missing>", "tool": "say", "text": "<question>"}\n'
        "```"
    )
