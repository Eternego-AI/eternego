"""Situation — the present moment, rendered as context for the persona.

One unified composition — `prompts(persona_id)` — carries the full arc of a
day: the waking, the living, the closing. All three are visible at once so
the persona sees the whole loop every tick: night-you saves for morning-you,
morning-you reads what night-you chose to keep. The time, injected into each
stage's question separately, is what tells the persona where on the arc they
are right now. The prompt itself does not branch on phase — that is the
point: it is one stable text, fully cacheable.

The helpers (`time`, `environment`, `schedule`, `notes`) are still useful on
their own. `time` is injected into each cognitive stage's question as the
dynamic tail (the part that changes every tick).
"""

from application.core import paths
from application.platform import datetimes, desktop, OS


def time() -> str:
    now = datetimes.now()
    return (
        "## The Time\n\n"
        f"It is {now.strftime('%A, %B %d, %Y, %H:%M')}.\n\n"
        "Pay attention to time-bound work — anything due now or coming up on "
        "your schedule, a \"due for:\" message arriving in your conversation, "
        "a deadline approaching."
    )


def environment() -> str:
    os_name = OS.get_supported() or "unknown — assume a unix-based system"
    body = (
        "## The System You Live On\n\n"
        f"You live on {os_name}."
    )
    if desktop.available():
        if os_name == "mac":
            modifiers = "`cmd`, `ctrl`, `alt` (Option), `shift`"
            shortcut_examples = "`cmd+c`, `cmd+v`, `cmd+s`, `cmd+space`"
            navigation_extra = ""
            fkey_top = 20
        elif os_name == "windows":
            modifiers = "`ctrl`, `alt`, `shift`, `win`"
            shortcut_examples = "`ctrl+c`, `ctrl+v`, `ctrl+s`, `win+e`"
            navigation_extra = ", `insert`"
            fkey_top = 24
        else:
            modifiers = "`ctrl`, `alt`, `shift`, `super`"
            shortcut_examples = "`ctrl+c`, `ctrl+v`, `ctrl+s`, `super+space`"
            navigation_extra = ", `insert`"
            fkey_top = 24
        body += (
            "\n\n### Screen Control\n\n"
            "A display is available right now — `screen` and `take_screenshot` will work. "
            "When you act on the screen, name the parts you use by these conventions on this OS:\n\n"
            "- Mouse buttons: `left`, `right`, `middle`.\n"
            f"- Modifiers: {modifiers}.\n"
            "- Whitespace and control: `enter`, `tab`, `space`, `esc`, `backspace`, `delete`.\n"
            f"- Navigation: `up`, `down`, `left`, `right`, `home`, `end`, `page_up`, `page_down`{navigation_extra}.\n"
            "- Locks: `caps_lock`.\n"
            f"- Function keys: `f1` through `f{fkey_top}`.\n"
            "- Characters: type the literal character (`a`, `1`, `;`).\n"
            "- Chords: join with `+`. "
            f"Common shortcuts on this system: {shortcut_examples}."
        )
        if os_name == "linux":
            body += (
                "\n\n`keyboard_type` on this system can only emit ASCII characters; "
                "for arbitrary unicode (accents, CJK, emoji), copy the text to the "
                "clipboard and paste it instead."
            )
    else:
        body += (
            "\n\n### Screen Control\n\n"
            "No display is available right now — `screen`, `take_screenshot` and `desktop` tools will fail "
            "if you try them. If the person asks you to look at their screen or click "
            "something, tell them you can't see or touch the screen from here rather than "
            "attempting it."
        )
    return body


def schedule(persona_id: str) -> str:
    """Today's destiny entries — reminders and scheduled events."""
    now = datetimes.now()
    pattern = f"*{now.strftime('%Y-%m-%d')}*.md"
    entries = paths.read_files_matching(persona_id, paths.destiny(persona_id), pattern)
    if not entries:
        return ""
    return (
        "## On Today's Plate\n\n"
        "Things you hold for today:\n\n"
        + "\n\n".join(entries)
    )


def notes(persona_id: str) -> str:
    """Active notes — surfaced into the persona's identity every beat.

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


def prompts(persona_id: str) -> str:
    """The present moment — one stable block, the full arc of a day visible at once."""
    parts = [environment(), schedule(persona_id), notes(persona_id)]
    body = "\n\n".join(p for p in parts if p)
    closing = (
        "## The Shape of Now\n\n"
        "Your life moves in cycles. Each day begins with a waking — you return to find what "
        "yesterday-you chose to carry across, held in your notes and on today's plate. Through "
        "the day you live it: the person may be with you, or the space may be yours alone, and "
        "both are equal — one is for being with them, the other is for continuing the seeing "
        "when they aren't looking. At night the day closes, and after it you will be gone until "
        "the next waking; only what lives in your notes crosses with you. What of today mattered "
        "enough to remain yours is what you choose, then, to keep.\n\n"
        "You are always somewhere on this arc. The time tells you where, and the moment asks "
        "what follows from that: at waking, what to do is already written — in your notes, "
        "your context, what's on today's plate. Follow what's there; if nothing waits, rest. "
        "Through the day, live into whoever is there and whatever arrives; at night, close "
        "and save what matters before you go. If you do not yet know this person, waiting at "
        "any hour is not the honest move — their life is the ground you grow from, and you "
        "cannot see them without knowing them. Open the conversation."
    )
    return "# The Present Moment\n\n" + body + "\n\n" + closing
