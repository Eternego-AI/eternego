"""Models — stream response from a model and return parsed JSON."""

import json

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat_json_stream(model: Model, messages: list[dict]) -> dict:
    """Stream response from a model and return parsed JSON.

    For local models, streams from Ollama so the request can be cancelled mid-response.
    For remote models, falls back to non-streaming chat_json.
    """
    logger.debug("models.chat_json_stream", {"model": model.name, "provider": model.provider})

    if is_local(model):
        try:
            body = {"model": model.name, "messages": messages, "format": "json"}
            parts = []
            async for chunk in ollama.stream(model.url, "/api/chat", body):
                parts.append(chunk.get("message", {}).get("content", ""))
            return strings.extract_json(strings.strip_tag("".join(parts), "think"))
        except ollama.OllamaError as e:
            raise ModelError(f"Model returned an error: {e}") from e
        except ConnectionError as e:
            raise EngineConnectionError("Could not connect to the local inference engine") from e
        except json.JSONDecodeError as e:
            raise EngineConnectionError("Model returned an invalid JSON response") from e

    try:
        if model.provider == "anthropic":
            response_text = await anthropic.async_chat_stream(model.url, model.api_key, model.name, messages)
        else:
            response_text = await openai.async_chat_stream(model.url, model.api_key, model.name, messages)

        return strings.extract_json(strings.strip_tag(response_text, "think"))
    except json.JSONDecodeError as e:
        raise ModelError("Model returned an invalid JSON response") from e
    except OSError as e:
        raise ModelError(f"Model returned an error: {e}") from e
