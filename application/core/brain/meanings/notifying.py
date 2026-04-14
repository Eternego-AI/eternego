"""Meaning — notifying the person about due events or important matters."""

from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"{persona.name} needs to notify the person about a due event or important matter"


def prompt(persona: Persona) -> str:
    return (
        "# Notify\n\n"
        "You need to notify the person about a due event, reminder, or important matter.\n"
        "Be clear about what is due, include the time, and mention any urgency.\n\n"
        "## Tools\n\n"
        "### say\n"
        "Send a message to the person.\n\n"
        "Parameters:\n"
        "- `text` (string, required): The notification message.\n\n"
        "## Response Format\n\n"
        "```json\n"
        '{"tool": "say", "text": "Hey, just a reminder: you have a meeting at 3pm today!"}\n'
        "```\n\n"
        "No special permissions are needed for notifications."
    )
