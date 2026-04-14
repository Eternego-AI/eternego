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
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise json.JSONDecodeError("No complete JSON object found", text, 0)
