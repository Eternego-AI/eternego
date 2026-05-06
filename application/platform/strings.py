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
    """Find the first valid JSON object in `text` starting from `start`.

    Returns the JSON text (including outer braces), or None if no parseable
    object is found. Uses `json.JSONDecoder.raw_decode` so balanced braces
    inside string literals (escaped quotes, nested JSON in `content` args,
    etc.) are not counted as object delimiters — naive brace counting
    breaks the moment a tool-call's payload contains JSON-shaped text.
    """
    decoder = json.JSONDecoder()
    idx = text.find("{", start)
    while idx != -1:
        try:
            _, end = decoder.raw_decode(text, idx)
            return text[idx:end]
        except json.JSONDecodeError:
            idx = text.find("{", idx + 1)
    return None




