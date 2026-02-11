"""External LLMs — parsing conversation data from external AI providers."""

import json

from application.platform import logger, anthropic, openai
from application.core.exceptions import ExternalDataError


async def read(data: str, source: str) -> str:
    """Parse external AI history into role-based text."""
    logger.info("Reading external LLM history", {"source": source})
    try:
        if source == "claude":
            return anthropic.role_based_text(data)

        return openai.role_based_text(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ExternalDataError("Could not parse external data") from e
