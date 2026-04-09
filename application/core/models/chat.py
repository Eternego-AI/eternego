"""Models — send messages to a model and return text."""

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat(model: Model, messages: list[dict]) -> str:
    """Send messages to a model and return the response text."""
    logger.debug("models.chat", {"model": model.name, "provider": model.provider})

    if is_local(model):
        try:
            response = await ollama.post(model.url, "/api/chat", {"model": model.name, "messages": messages, "stream": False})
            return strings.strip_tag(response.get("message", {}).get("content", ""), "think")
        except ollama.OllamaError as e:
            raise ModelError(f"Model returned an error: {e}") from e
        except ConnectionError as e:
            raise EngineConnectionError("Could not connect to the local inference engine") from e
        except KeyError as e:
            logger.warning("models.chat invalid response", {"model": model.name, "response": str(response)})
            raise EngineConnectionError("Model returned an invalid response") from e

    api_key = (model.credentials or {}).get("api_key", "")

    try:
        if model.provider == "anthropic":
            return await anthropic.async_chat(model.url, api_key, model.name, messages)

        return await openai.async_chat(model.url, api_key, model.name, messages)
    except OSError as e:
        raise ModelError(f"Model returned an error: {e}") from e
