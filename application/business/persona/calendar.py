"""Persona — what she has in her calendar between two dates.

This is a view of what she keeps on disk, not a calendar engine. Recurring
items are her own decision — when a weekly reminder fires, *she* writes the
next one. So we don't project anything; we just read what's there.

Two on-disk shapes feed this:

- `history/` — past events the persona archived. Three subtypes from the
  filename prefix: `conversation`, `schedule`, `reminder`. `briefing.md` is
  her internal index mapping a filename to its precise ISO timestamp, used
  here only to enrich conversation entries (whose filenames carry the date
  but not the time).
- `destiny/` — events she's scheduled. Two subtypes from the prefix:
  `schedule`, `reminder`. The `recurrence:` line in the body is informative
  (the UI can label it), but we project nothing.

The spec returns the two halves grouped by subtype so the reader can see
exactly what kind of thing she keeps and the web can colour each
differently.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Persona
from application.platform import logger


@dataclass
class CalendarData:
    history: dict[str, list[dict]] = field(default_factory=dict)
    destiny: dict[str, list[dict]] = field(default_factory=dict)


HISTORY_SUBTYPES = ("conversation", "schedule", "reminder")
DESTINY_SUBTYPES = ("schedule", "reminder")

_NAME_RE = re.compile(r"^([a-z]+)-(\d{4})-(\d{2})-(\d{2})(?:-(\d{2})-(\d{2}))?")
_BRIEFING_RE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.\d]*[+\-]\d{2}:\d{2}):\s*(.+?\.md)\s*$")


def _parse_filename(stem: str) -> tuple[str, datetime] | None:
    """Filename → (subtype prefix, datetime). Returns None for non-matching names."""
    m = _NAME_RE.match(stem)
    if not m:
        return None
    try:
        y, mo, d = int(m.group(2)), int(m.group(3)), int(m.group(4))
        hh = int(m.group(5)) if m.group(5) else 0
        mm = int(m.group(6)) if m.group(6) else 0
        return m.group(1), datetime(y, mo, d, hh, mm)
    except (ValueError, IndexError):
        return None


def _briefing_index(persona_id: str) -> dict[str, str]:
    """Map history filename → ISO timestamp, read from briefing.md.

    Briefing is her internal index — lines like
    `- 2026-04-17T00:01:38.564+02:00: conversation-2026-04-17.md`.
    """
    out: dict[str, str] = {}
    briefing = paths.history_briefing(persona_id)
    if not briefing.exists():
        return out
    for line in paths.read(briefing).splitlines():
        m = _BRIEFING_RE.match(line.strip())
        if m:
            out[m.group(2)] = m.group(1)
    return out


def _read_recurrence_and_body(content: str) -> tuple[str | None, str]:
    """Pull a `recurrence: <kind>` line out of a destiny body; return the rest."""
    recurrence: str | None = None
    lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("recurrence:"):
            recurrence = stripped.split(":", 1)[1].strip().lower() or None
        else:
            lines.append(line)
    return recurrence, "\n".join(lines).strip()


async def calendar(persona: Persona, start: datetime, end: datetime) -> Outcome[CalendarData]:
    """Read all of `history/` and `destiny/`, filter to events whose timestamp
    is in [start, end), and group by subtype.

    Past events keep only the subtypes she actually writes (`conversation`,
    `schedule`, `reminder`); future events similarly (`schedule`, `reminder`).
    Anything else on disk is ignored — it's not a calendar event.
    """
    bus.propose("Reading persona calendar", {"persona": persona, "start": start.isoformat(), "end": end.isoformat()})
    try:
        history = {sub: [] for sub in HISTORY_SUBTYPES}
        destiny = {sub: [] for sub in DESTINY_SUBTYPES}

        briefing_map = _briefing_index(persona.id)
        for f in paths.md_files(paths.history(persona.id)):
            if f.name == "briefing.md":
                continue
            parsed = _parse_filename(f.stem)
            if not parsed:
                continue
            name, when = parsed
            if name not in history:
                continue
            if not (start <= when < end):
                continue
            body = paths.read(f)
            if not body:
                continue
            history[name].append({
                "time": briefing_map.get(f.name) or when.isoformat(),
                "body": body,
            })

        for f in paths.md_files(paths.destiny(persona.id)):
            parsed = _parse_filename(f.stem)
            if not parsed:
                continue
            name, when = parsed
            if name not in destiny:
                continue
            if not (start <= when < end):
                continue
            content = paths.read(f)
            if not content:
                continue
            recurrence, body = _read_recurrence_and_body(content)
            destiny[name].append({
                "time": when.isoformat(),
                "body": body,
                "recurrence": recurrence,
            })

        bus.broadcast("Persona calendar read", {
            "persona": persona,
            "history": {k: len(v) for k, v in history.items()},
            "destiny": {k: len(v) for k, v in destiny.items()},
        })
        return Outcome(success=True, message="", data=CalendarData(history=history, destiny=destiny))
    except Exception as e:
        logger.warning("Could not read persona calendar", {"persona": persona, "error": str(e)})
        bus.broadcast("Persona calendar read failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not read calendar.")
