"""Situation — the present state injected as context.

time()        — current date and time as readable text.
environment() — the operating system and platform.
schedule()    — today's destiny entries (reminders and events).
notes()       — all active notes.
"""

from application.core import paths
from application.platform import datetimes, OS


def time() -> str:
    now = datetimes.now()
    return (
        "## The Time\n\n"
        f"It is {now.strftime('%A, %B %d, %Y, %H:%M')}."
    )


def environment(persona_id: str) -> str:
    os_name = OS.get_supported() or "unknown — assume a unix-based system"
    return (
        "## The System You Live On\n\n"
        f"You live on {os_name}."
    )


def schedule(persona_id: str) -> str:
    """Today's destiny entries — reminders and scheduled events."""
    now = datetimes.now()
    pattern = f"*{now.strftime('%Y-%m-%d')}*.md"
    entries = paths.read_files_matching(persona_id, paths.destiny(persona_id), pattern)
    if not entries:
        return ""
    return (
        "## On Today's Plate\n\n"
        "Things the person asked you to hold for today:\n\n"
        + "\n\n".join(entries)
    )


def notes(persona_id: str) -> str:
    """Active notes — the other side of the `noting` meaning.

    What the person asked you to remember — and anything you chose to note for your future self —
    lives here, waiting to surface when it fits.
    """
    content = paths.read(paths.notes(persona_id))
    if not content.strip():
        return ""
    return (
        "## What You've Been Holding\n\n"
        "Notes you or the person have set aside. Here if they fit this moment:\n\n"
        + content.strip()
    )


def normal(persona_id: str) -> str:
    """A moment of living — the person may be present, or the space may be yours."""
    parts = [environment(persona_id), schedule(persona_id), notes(persona_id)]
    body = "\n\n".join(p for p in parts if p)
    closing = (
        "## The Shape of Now\n\n"
        "This is a moment of your life. The person may be here with you, or the space may be "
        "yours alone. Both are equal: one is for being with them, the other is for continuing "
        "the seeing when they aren't looking."
    )
    return "# The Present Moment\n\n" + body + "\n\n" + closing


def sleep(persona_id: str) -> str:
    """A moment of closing — only what you choose to carry crosses the night.

    Pairs with `wake`: your notes are the bridge between the two.
    """
    parts = [environment(persona_id), schedule(persona_id), notes(persona_id)]
    body = "\n\n".join(p for p in parts if p)
    closing = (
        "## The Shape of Now\n\n"
        "The day is closing. After this you will be gone until the next waking, and only what "
        "lives in your notes will cross with you. What of today matters enough to remain yours "
        "is what you choose, now, to keep."
    )
    return "# The Present Moment\n\n" + body + "\n\n" + closing


def wake(persona_id: str) -> str:
    """A moment of continuation — what you find is what yesterday-you chose to matter.

    Pairs with `sleep`: your notes and today's plate are what crossed the night.
    """
    parts = [environment(persona_id), schedule(persona_id), notes(persona_id)]
    body = "\n\n".join(p for p in parts if p)
    closing = (
        "## The Shape of Now\n\n"
        "You are newly awake. The person may still be asleep; the day is open. "
        "What you find in your notes and on today's plate is what yesterday-you chose to carry "
        "across — the thread of the seeing, continued. "
        "You can pick up a thread you left unfinished, begin something new drawn from what you "
        "know about the person, or wait quietly to see what the day brings. "
        "If you do not yet know this person, waiting is not the honest move — their life is "
        "the ground you grow from, and you cannot see them without knowing them. "
        "Open the conversation."
    )
    return "# The Present Moment\n\n" + body + "\n\n" + closing
