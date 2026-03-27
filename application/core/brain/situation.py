"""Situation — the present state injected as context.

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


def environment(persona_id: str) -> str:
    os_name = OS.get_supported() or "is unknown, consider a unix based os"
    ws = paths.workspace(persona_id)
    return (
        f"Current OS: {os_name}\n"
        "When running commands, installing software, or suggesting system operations, "
        "use commands and packages appropriate for this OS.\n"
        f"Workspace: {ws}\n"
        "When creating files for the person (documents, spreadsheets, code, images, exports), "
        "save them to the workspace unless the person specifies a different location."
    )


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


def normal(persona_id: str) -> str:
    parts = [time(), environment(persona_id), schedule(persona_id), notes(persona_id)]
    return "\n\n".join(p for p in parts if p)


def sleep(persona_id: str) -> str:
    parts = [time(), environment(persona_id), schedule(persona_id), notes(persona_id), (
        'You are going to sleep now. Take a note from what are not completed today and what you want to focus on tomorrow.'
    )]
    return "\n\n".join(p for p in parts if p)


def wake(persona_id: str) -> str:
    parts = [time(), environment(persona_id), schedule(persona_id), notes(persona_id), (
        'You just woke up. Read notes and schedule to get a sense of what is on your plate today. If there are any notes'
        ' about what to focus on, prioritize those.'
    )]
    return "\n\n".join(p for p in parts if p)
