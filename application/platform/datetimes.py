"""Datetimes — date and time operations."""

from datetime import datetime, timezone


def now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def iso_8601(dt: datetime) -> str:
    """Format a datetime as an ISO 8601 string."""
    return dt.isoformat()


def stamp(dt: datetime) -> str:
    """Format a datetime as a compact timestamp (YYYYMMDDHHmmSS)."""
    return dt.strftime("%Y%m%d%H%M%S")


def date_stamp(dt: datetime) -> str:
    """Format a datetime as a date string (YYYY-MM-DD)."""
    return dt.strftime("%Y-%m-%d")


def from_stamp(text: str) -> datetime:
    """Parse a compact timestamp back to a UTC datetime."""
    return datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def to_utc(local_str: str, tz_name: str) -> datetime:
    """Convert a local datetime string (YYYY-MM-DD HH:MM) in tz_name to UTC."""
    import zoneinfo
    tz = zoneinfo.ZoneInfo(tz_name)
    local_dt = datetime.strptime(local_str, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def system_timezone() -> str:
    """Return the IANA timezone name of the local system."""
    import os
    local_tz = datetime.now().astimezone().tzinfo
    if hasattr(local_tz, "key"):
        return local_tz.key
    localtime = "/etc/localtime"
    if os.path.islink(localtime):
        target = os.readlink(localtime)
        if "zoneinfo/" in target:
            return target.split("zoneinfo/")[-1]
    return "UTC"
