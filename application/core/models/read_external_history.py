"""Models — parse external AI history into messages."""

import json

from application.core.exceptions import ModelError
from application.platform import logger, anthropic, openai


async def read_external_history(data: str, source: str) -> list[dict]:
    """Parse external AI history into role-based messages."""
    logger.info("models.read_external_history", {"source": source})
    try:
        if source == "claude":
            return anthropic.to_messages(data)
        return openai.to_messages(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ModelError("Could not parse external data") from e
