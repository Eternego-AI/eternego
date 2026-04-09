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


def extract_json(text: str) -> dict:
    """Extract and parse the first JSON object from text, handling code fences and surrounding prose."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    return json.loads(text[start:end + 1])
