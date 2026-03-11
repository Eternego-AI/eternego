"""Current — the present state injected as context.

time()        — current date and time as readable text.
environment() — the operating system and platform.
"""

from application.platform import datetimes, OS


def time() -> str:
    now = datetimes.now()
    return (
        f"Current time: {now.strftime('%A, %B %d, %Y %H:%M UTC')}\n"
    )


def environment() -> str:
    os_name = OS.get_supported() or "is unknown, consider a unix based os"
    return f"Environment: {os_name}"


def situation(persona) -> str:
    parts = [time(), environment()]
    return "\n".join(p for p in parts if p)
