"""Models — send messages to a model and return text."""

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat(model: Model, messages: list[dict]) -> str:
    """Stream messages to a model and return the complete response text."""
    logger.debug("models.chat", {"model": model.name, "provider": model.provider, "messages": messages})

    try:
        parts = []
        if is_local(model):
            async for chunk in ollama.chat(model.url, model.name, messages):
                parts.append(chunk)
        elif model.provider == "anthropic":
            async for chunk in anthropic.chat(model.url, model.api_key, model.name, messages):
                parts.append(chunk)
        else:
            async for chunk in openai.chat(model.url, model.api_key, model.name, messages):
                parts.append(chunk)
        return strings.strip_tag("".join(parts), "think")
    except ollama.OllamaError as e:
        raise ModelError(f"Model returned an error: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except OSError as e:
        raise ModelError(f"Model returned an error: {e}") from e
