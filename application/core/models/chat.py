"""Models — send messages to a model and return text."""

from application.core.data import Model
from application.core.exceptions import EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat(model: Model, identity: str, reality: list[dict], question: str) -> str:
    """Stream messages to a model and return the complete response text."""
    messages = []
    if identity:
        messages.append({"role": "system", "content": identity})
    messages.extend(reality)
    messages.append({"role": "user", "content": question})
    logger.debug("models.chat", {"model": model.name, "provider": model.provider, "messages": messages})

    try:
        parts = []
        if is_local(model):
            async for chunk in ollama.chat(model.url, model.name, messages):
                parts.append(chunk)
        elif model.provider == "anthropic":
            for msg in messages:
                if msg.get("role") == "system":
                    msg["cache_control"] = "ephemeral"
                elif msg.pop("cache_point", False):
                    msg["cache_control"] = "ephemeral"
            async for chunk in anthropic.chat(model.url, model.api_key, model.name, messages):
                parts.append(chunk)
        else:
            async for chunk in openai.chat(model.url, model.api_key, model.name, messages):
                parts.append(chunk)
        return strings.strip_tag("".join(parts), "think")
    except ollama.OllamaError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
    except ConnectionError as e:
        raise EngineConnectionError(f"Could not reach model service: {e}", model=model) from e
    except OSError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
