"""Frontier — escalation to a more powerful external model."""

import asyncio
from urllib.error import URLError

from application.platform import logger
from application.platform import anthropic as anthropic_platform
from application.platform import openai as openai_platform
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
            return await asyncio.to_thread(openai_platform.respond, api_key, model.name, messages)
        if provider == "anthropic":
            return await asyncio.to_thread(anthropic_platform.respond, api_key, model.name, messages)
        raise FrontierError(f"Unsupported frontier provider: {provider}")
    except (URLError, OSError) as e:
        raise FrontierError(f"Failed to contact frontier model: {e}") from e


