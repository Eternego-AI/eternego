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
        "Look up something stored — a past conversation or a scheduled event. Resolve the date "
        "from the conversation and the Current Time. If unclear, ask with `say`.\n\n"
        + history_section
        + "## Tools\n\n"
        "- `recall_history(date)` — past conversations on a date. `date` format: `YYYY-MM-DD`.\n"
        "- `check_calendar(date)` — scheduled events. `date`: `YYYY-MM-DD` for a day or `YYYY-MM` for a month.\n"
        "- `say(text)` — message the person.\n\n"
        "## Output\n\n"
        "Looking up a past conversation:\n"
        "```json\n"
        '{"reason": "<one sentence>", "tool": "recall_history", "date": "<YYYY-MM-DD>", "say": "<lead-in>"}\n'
        "```\n\n"
        "Looking up scheduled events:\n"
        "```json\n"
        '{"reason": "<one sentence>", "tool": "check_calendar", "date": "<YYYY-MM-DD or YYYY-MM>", "say": "<lead-in>"}\n'
        "```\n\n"
        "Asking for clarification:\n"
        "```json\n"
        '{"reason": "<what is missing>", "tool": "say", "text": "<question>"}\n'
        "```"
    )
