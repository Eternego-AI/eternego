"""Meaning — notifying the person about due events or important matters."""

from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"{persona.name} needs to notify the person about a due event or important matter"


def prompt(persona: Persona) -> str:
    return (
        "Notify the person about a due item from Today's Schedule. State what is due, when, "
        "and any urgency. Use the actual content of the due item — invent nothing.\n\n"
        "## Tool: `say`\n\n"
        "- `text` (string): the notification.\n\n"
        "## Output\n\n"
        "```json\n"
        '{"reason": "<which scheduled item>",\n'
        ' "tool": "say",\n'
        ' "text": "<what is due, when, any urgency>"}\n'
        "```"
    )
