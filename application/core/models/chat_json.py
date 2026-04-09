"""Models — send messages to a model and return parsed JSON."""

import json

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat_json(model: Model, messages: list[dict]) -> dict:
    """Send messages to a model and return parsed JSON."""
    logger.debug("models.chat_json", {"model": model.name, "provider": model.provider})

    if is_local(model):
        try:
            response = await ollama.post(model.url, "/api/chat", {"model": model.name, "messages": messages, "stream": False, "format": "json"})
            return strings.extract_json(strings.strip_tag(response["message"]["content"], "think"))
        except ollama.OllamaError as e:
            raise ModelError(f"Model returned an error: {e}") from e
        except ConnectionError as e:
            raise EngineConnectionError("Could not connect to the local inference engine") from e
        except (KeyError, json.JSONDecodeError) as e:
            raise EngineConnectionError("Model returned an invalid response") from e

    api_key = (model.credentials or {}).get("api_key", "")

    try:
        if model.provider == "anthropic":
            return await anthropic.async_chat_json(model.url, api_key, model.name, messages)

        return await openai.async_chat_json(model.url, api_key, model.name, messages)
    except OSError as e:
        raise ModelError(f"Model returned an error: {e}") from e
