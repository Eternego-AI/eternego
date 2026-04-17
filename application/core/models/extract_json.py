"""Models — extract the first JSON object from model output."""

import json

from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.strings import extract_braces


def extract_json(text: str) -> dict:
    """Find the first valid JSON object in model output."""
    logger.debug("models.extract_json", {"raw": text})
    block = extract_braces(text)
    if block is None:
        raise ModelError("No JSON object found in model response")
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        raise ModelError("Model response contains malformed JSON")
