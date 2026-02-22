"""Frontier — escalation to a more powerful external model."""

import asyncio, json
from urllib.error import URLError

from application.platform import logger
from application.platform import anthropic
from application.platform import openai
from application.core.data import Model
from application.core.exceptions import FrontierError


async def respond(model: Model, prompt: str) -> str:
    """Send a prompt to a frontier model and return the response."""
    logger.info("Responding via frontier", {"model": model.name})
    messages = [{"role": "user", "content": prompt}]
    creds = model.credentials or {}
    provider = model.provider or "openai"
    api_key = creds.get("api_key", "")

    try:
        if provider == "openai":
            return await asyncio.to_thread(openai.respond, api_key, model.name, messages)
        if provider == "anthropic":
            return await asyncio.to_thread(anthropic.respond, api_key, model.name, messages)
        raise FrontierError(f"Unsupported frontier provider: {provider}")
    except (URLError, OSError) as e:
        raise FrontierError(f"Failed to contact frontier model: {e}") from e


async def read(data: str, source: str) -> str:
    """Parse external AI history into role-based text."""
    logger.info("Reading external LLM history", {"source": source})
    try:
        if source == "claude":
            return anthropic.role_based_text(data)

        return openai.role_based_text(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise FrontierError("Could not parse external data") from e

