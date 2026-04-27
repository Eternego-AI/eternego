"""Health log shaping for web display.

Takes the raw heartbeat entries (read directly from the persona's
`health.jsonl` file) and turns them into the shapes the UI needs:

- `uptime_grid(entries)` — a 24×60 grid of the last 1440 minutes for the
  status page's uptime view: row 0 holds the most recent 60 loops, row 23
  the oldest. Within each row, the leftmost cell is the latest loop in
  that block.
- `lenses(entries)` — three rolled-up summaries (last 7 days, last 24
  hours, last 60 minutes). Currently unused but kept for reuse if a more
  zoomed-out vitals view returns.
"""

from datetime import datetime, timedelta

from application.platform import datetimes as dt


def _parse(entry, now_tz):
    stamp = entry.get("time", "")
    try:
        t = datetime.fromisoformat(stamp)
    except Exception:
        return None
    if t.tzinfo is None and now_tz is not None:
        t = t.replace(tzinfo=now_tz)
    return t


def lenses(entries, days_count=7, hours_count=24, minutes_count=60):
    """Three lenses on the same body — daily, hourly, minute roll-ups."""
    now = dt.now()
    day_cutoff = (now - timedelta(days=days_count - 1)).date()
    hour_cutoff = (now - timedelta(hours=hours_count - 1)).replace(minute=0, second=0, microsecond=0)
    minute_cutoff = (now - timedelta(minutes=minutes_count - 1)).replace(second=0, microsecond=0)

    day_bins: dict[str, dict] = {}
    hour_bins: dict[str, dict] = {}
    minute_bins: dict[str, dict] = {}

    for entry in entries:
        t = _parse(entry, now.tzinfo)
        if t is None:
            continue
        fault_count = entry.get("fault_count", 0) or 0
        providers = entry.get("fault_providers", []) or []

        if t.date() >= day_cutoff:
            slot = day_bins.setdefault(str(t.date()), {"ticks": 0, "faults": 0, "providers": set()})
            slot["ticks"] += 1
            if fault_count > 0:
                slot["faults"] += 1
                slot["providers"].update(providers)

        if t >= hour_cutoff:
            key = t.replace(minute=0, second=0, microsecond=0).isoformat()
            slot = hour_bins.setdefault(key, {"ticks": 0, "faults": 0, "providers": set()})
            slot["ticks"] += 1
            if fault_count > 0:
                slot["faults"] += 1
                slot["providers"].update(providers)

        if t >= minute_cutoff:
            key = t.replace(second=0, microsecond=0).isoformat()
            slot = minute_bins.setdefault(key, {"ticks": 0, "faults": 0, "providers": set()})
            slot["ticks"] += 1
            if fault_count > 0:
                slot["faults"] += fault_count
                slot["providers"].update(providers)

    days = []
    for offset in range(days_count):
        d = day_cutoff + timedelta(days=offset)
        slot = day_bins.get(str(d), {"ticks": 0, "faults": 0, "providers": set()})
        days.append({
            "at": str(d),
            "ticks": slot["ticks"],
            "faults": slot["faults"],
            "fault_providers": sorted(slot["providers"]),
        })

    hours = []
    for offset in range(hours_count):
        h = hour_cutoff + timedelta(hours=offset)
        slot = hour_bins.get(h.isoformat(), {"ticks": 0, "faults": 0, "providers": set()})
        hours.append({
            "at": h.isoformat(),
            "ticks": slot["ticks"],
            "faults": slot["faults"],
            "fault_providers": sorted(slot["providers"]),
        })

    minutes = []
    for offset in range(minutes_count):
        m = minute_cutoff + timedelta(minutes=offset)
        slot = minute_bins.get(m.isoformat(), {"ticks": 0, "faults": 0, "providers": set()})
        minutes.append({
            "at": m.isoformat(),
            "ticks": slot["ticks"],
            "faults": slot["faults"],
            "fault_providers": sorted(slot["providers"]),
        })

    return {"days": days, "hours": hours, "minutes": minutes}


def uptime_grid(entries, rows_count=24, cols_count=60):
    """24-hour minute-by-minute grid, latest first.

    Returns `{"rows": [{from, to, cells: [{at, tick, fault, providers, signals}, …]}, …]}`.
    Row 0 is the most recent block of `cols_count` minutes; within each row,
    the leftmost cell is the latest minute in that block. `signals` is the
    list of signals captured during that minute's health-check window —
    used by the UI to surface a per-cell timeline on click.
    """
    now = dt.now()
    now_minute = now.replace(second=0, microsecond=0)
    cutoff = now_minute - timedelta(minutes=(rows_count * cols_count) - 1)

    minute_bins: dict[str, dict] = {}
    for entry in entries:
        t = _parse(entry, now.tzinfo)
        if t is None:
            continue
        m = t.replace(second=0, microsecond=0)
        if m < cutoff or m > now_minute:
            continue
        key = m.isoformat()
        slot = minute_bins.setdefault(key, {"fault": False, "providers": set(), "signals": []})
        if entry.get("fault_count", 0) > 0:
            slot["fault"] = True
            slot["providers"].update(entry.get("fault_providers", []) or [])
        slot["signals"].extend(entry.get("signals", []) or [])

    rows = []
    for row_idx in range(rows_count):
        cells = []
        for col_idx in range(cols_count):
            offset = row_idx * cols_count + col_idx
            m = now_minute - timedelta(minutes=offset)
            slot = minute_bins.get(m.isoformat())
            if slot is not None:
                cells.append({
                    "at": m.isoformat(),
                    "tick": True,
                    "fault": slot["fault"],
                    "providers": sorted(slot["providers"]),
                    "signals": slot["signals"],
                })
            else:
                cells.append({
                    "at": m.isoformat(),
                    "tick": False,
                    "fault": False,
                    "providers": [],
                    "signals": [],
                })
        rows.append({
            "from": cells[-1]["at"],
            "to": cells[0]["at"],
            "cells": cells,
        })

    return {"rows": rows}
