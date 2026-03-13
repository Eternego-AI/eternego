"""Current — the present state injected as context.

time()        — current date and time as readable text.
environment() — the operating system and platform.
schedule()    — today's destiny entries (reminders and events).
notes()       — all active notes.
"""

from application.core import paths, system
from application.platform import datetimes, OS


def time() -> str:
    now = datetimes.now()
    return (
        f"Current time: {now.strftime('%A, %B %d, %Y %H:%M UTC')}.\n"
        "Always express times in the person's timezone from person identity. "
        f"If not available, use {system.timezone()}."
    )


def environment() -> str:
    os_name = OS.get_supported() or "is unknown, consider a unix based os"
    return f"Environment: {os_name}"


def schedule(persona_id: str) -> str:
    """Today's destiny entries — reminders and scheduled events."""
    now = datetimes.now()
    pattern = f"*{now.strftime('%Y-%m-%d')}*.md"
    entries = paths.read_files_matching(persona_id, paths.destiny(persona_id), pattern)
    if not entries:
        return ""
    return "# Today's Schedule\n" + "\n\n".join(entries)


def notes(persona_id: str) -> str:
    """All active notes."""
    entries = paths.read_files_matching(persona_id, paths.notes(persona_id), "*.md")
    if not entries:
        return ""
    return "# Notes\n" + "\n\n".join(entries)


def situation(persona_id: str) -> str:
    parts = [time(), environment(), schedule(persona_id), notes(persona_id)]
    return "\n\n".join(p for p in parts if p)
