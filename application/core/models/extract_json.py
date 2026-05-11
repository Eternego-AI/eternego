"""Models — extract the JSON object from model output. Strict: the response
must contain a parseable JSON object, no prose fallback."""

import json

from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.strings import extract_braces


def extract_json(text: str) -> dict:
    """Find the first valid JSON object in model output.

    Raises ModelError if no balanced JSON object is found or if it doesn't
    parse. Callers expecting a strict JSON contract should let this raise.
    """
    logger.debug("models.extract_json", {"raw": text})
    block = extract_braces(text)
    if block is None:
        raise ModelError("No JSON object found in model response", raw=text)
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        raise ModelError("Model response contains malformed JSON", raw=text)
