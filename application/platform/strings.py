"""Strings — string parsing utilities."""

import json


def to_json(text: str) -> dict:
    """Parse a JSON string into a dict, returning an empty dict on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}


def strip_tag(text: str, tag: str) -> str:
    """Remove all occurrences of <tag>...</tag> from text."""
    import re
    return re.sub(rf"<{tag}>.*?</{tag}>", "", text, flags=re.DOTALL).strip()


def extract_braces(text: str, start: int = 0) -> str | None:
    """Find the first balanced {...} block starting from `start`, recursively.

    Returns the balanced text including outer braces, or None if not found.
    """
    opening = text.find("{", start)
    if opening == -1:
        return None

    result = "{"
    cursor = opening + 1

    while cursor < len(text):
        next_open = text.find("{", cursor)
        next_close = text.find("}", cursor)

        if next_close == -1:
            return None

        if next_open == -1 or next_close < next_open:
            result += text[cursor:next_close + 1]
            return result

        result += text[cursor:next_open]
        inner = extract_braces(text, next_open)
        if inner is None:
            return None
        result += inner
        cursor = next_open + len(inner)

    return None




