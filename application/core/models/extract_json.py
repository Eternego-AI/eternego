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
        raise ModelError("No JSON object found in model response", raw=text)
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        raise ModelError("Model response contains malformed JSON", raw=text)


def extract_action(text: str) -> tuple[str, dict]:
    """Find the JSON action and return (prose, action). Prose is anything in
    the model's output outside the JSON block, with code-fence markers stripped.

    Used by recognize and decide so that natural-language prose around a JSON
    action gets honored as the persona's voice — intelligence is words after
    words, and when the model writes both, the words are the saying and the
    JSON is the action."""
    logger.debug("models.extract_action", {"raw": text})
    block = extract_braces(text)
    if block is None:
        raise ModelError("No JSON object found in model response", raw=text)
    try:
        parsed = json.loads(block)
    except json.JSONDecodeError:
        raise ModelError("Model response contains malformed JSON", raw=text)
    prose = text.replace(block, "", 1)
    prose = prose.replace("```json", "").replace("```", "").strip()
    return prose, parsed
