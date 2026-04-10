"""Models — stream response from a model and return text."""

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat_stream(model: Model, messages: list[dict]) -> str:
    """Stream response from a model and return the full text.

    Uses streaming to avoid hard timeouts on slow/thinking models.
    """
    logger.debug("models.chat_stream", {"model": model.name, "provider": model.provider})

    if is_local(model):
        try:
            body = {"model": model.name, "messages": messages}
            parts = []
            async for chunk in ollama.stream(model.url, "/api/chat", body):
                parts.append(chunk.get("message", {}).get("content", ""))
            return strings.strip_tag("".join(parts), "think")
        except ollama.OllamaError as e:
            raise ModelError(f"Model returned an error: {e}") from e
        except ConnectionError as e:
            raise EngineConnectionError("Could not connect to the local inference engine") from e

    try:
        if model.provider == "anthropic":
            return await anthropic.async_chat_stream(model.url, model.api_key, model.name, messages)
        return await openai.async_chat_stream(model.url, model.api_key, model.name, messages)
    except OSError as e:
        raise ModelError(f"Model returned an error: {e}") from e
