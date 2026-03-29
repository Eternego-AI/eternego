"""Datetimes — date and time operations."""

from datetime import datetime


def now() -> datetime:
    """Return the current local datetime."""
    return datetime.now().astimezone()


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
    """Parse a compact timestamp back to a local datetime."""
    return datetime.strptime(text, "%Y%m%d%H%M%S").astimezone()
