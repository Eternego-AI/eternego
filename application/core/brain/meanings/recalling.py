"""Meaning — recalling past conversations and scheduled events."""

from application.core import paths
from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"The person wants {persona.name} to recall a past conversation or check scheduled events"


def prompt(persona: Persona) -> str:
    briefing = paths.read(paths.history_briefing(persona.id))
    history_section = (
        f"## Past Conversations\n\n{briefing}\n\n" if briefing.strip()
        else "No past conversations on record yet.\n\n"
    )
    return (
        "# Recalling\n\n"
        "The person wants to look up something stored — a past conversation or a scheduled event.\n\n"
        + history_section
        + "## Tools\n\n"
        "### recall_history\n"
        "Look up past conversations from a specific date.\n\n"
        "Parameters:\n"
        "- `date` (string, required): The date to look up, format `\"YYYY-MM-DD\"`\n\n"
        "### check_calendar\n"
        "Look up scheduled events and reminders.\n\n"
        "Parameters:\n"
        "- `date` (string, required): Date to look up. "
        "Use `\"YYYY-MM-DD\"` for a specific day or `\"YYYY-MM\"` for an entire month.\n\n"
        "### say\n"
        "Send a message to the person.\n\n"
        "Parameters:\n"
        "- `text` (string, required): The message to send.\n\n"
        "## Response Format\n\n"
        "For past conversations:\n"
        "```json\n"
        '{"tool": "recall_history", "date": "2026-04-10", '
        '"say": "Here\'s what we discussed:"}\n'
        "```\n\n"
        "For scheduled events:\n"
        "```json\n"
        '{"tool": "check_calendar", "date": "2026-04-14", '
        '"say": "Here\'s what you have scheduled:"}\n'
        "```\n\n"
        "If the date is unclear, use say to ask. "
        "No special permissions are needed for recalling."
    )
