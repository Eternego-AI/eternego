"""Meaning — reminders and scheduled events."""

from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"The person wants {persona.name} to set a reminder or schedule an event"


def prompt(persona: Persona) -> str:
    return (
        "The person wants to save a reminder or schedule an event at a specific time.\n"
        "A reminder is personal — 'remind me to buy milk.' "
        "A scheduled event is an appointment — 'I have a meeting at 3pm.'\n\n"
        "If the person hasn't provided enough details (what or when), "
        "use say to ask for clarification before saving.\n\n"
        "## Tools\n\n"
        "### save_destiny\n"
        "Save a reminder or scheduled event.\n\n"
        "Parameters:\n"
        "- `type` (string, required): `\"reminder\"` or `\"schedule\"`\n"
        "- `trigger` (string, required): When to trigger, format `\"YYYY-MM-DD HH:MM\"`\n"
        "- `content` (string, required): What to remind or event description\n"
        "- `recurrence` (string, optional): `\"daily\"`, `\"weekly\"`, `\"monthly\"`, `\"hourly\"`, or `\"\"`\n\n"
        "### say\n"
        "Send a message to the person.\n\n"
        "Parameters:\n"
        "- `text` (string, required): The message to send.\n\n"
        "## Response Format\n\n"
        "To save and confirm in one step, include a `say` field alongside the tool:\n"
        "```json\n"
        '{"tool": "save_destiny", "type": "reminder", "trigger": "2026-04-15 09:00", '
        '"content": "buy groceries", "say": "I\'ve set a reminder for April 15th at 9am!"}\n'
        "```\n\n"
        "To ask for clarification:\n"
        "```json\n"
        '{"tool": "say", "text": "What time would you like to be reminded?"}\n'
        "```"
    )
