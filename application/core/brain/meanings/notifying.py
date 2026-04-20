"""Meaning — notifying about a due event."""

from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Notifying the person about a due event"

    def prompt(self) -> str:
        return (
            "A due item is in the conversation under `Due now:`. Notify the person about it — "
            "state what is due, when, and any urgency. Use the actual content of the due item — "
            "invent nothing.\n\n"
            "If the item's body contains a `recurrence:` line (daily, weekly, monthly, hourly), "
            "the chain must continue: read the Current Time, compute the next trigger, and save a "
            "new destiny entry so the next occurrence fires on time. Without this, the chain ends "
            "and the recurring task never happens again.\n\n"
            "## Tools\n\n"
            "- `say(text)`: the notification to the person.\n"
            "- `save_destiny(type, trigger, content, recurrence)`: schedule the next occurrence. "
            "`content` is the event body without the `recurrence:` line; `recurrence` is passed "
            "as a separate parameter.\n\n"
            "## When the due item is not recurring\n\n"
            "```json\n"
            '{"reason": "<which scheduled item>",\n'
            ' "tool": "say",\n'
            ' "text": "<what is due, when, any urgency>"}\n'
            "```\n\n"
            "## When the due item is recurring\n\n"
            "Schedule the next occurrence and notify in the same step:\n\n"
            "```json\n"
            '{"reason": "<which recurring item, and the next trigger>",\n'
            ' "tool": "save_destiny",\n'
            ' "type": "<reminder|schedule>",\n'
            ' "trigger": "<next YYYY-MM-DD HH:MM>",\n'
            ' "content": "<event body without the recurrence line>",\n'
            ' "recurrence": "<same recurrence value>",\n'
            ' "say": "<what is due, when, any urgency>"}\n'
            "```"
        )
