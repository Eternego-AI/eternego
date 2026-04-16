"""Models — send messages to a model and return parsed JSON."""

import json

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat_json(model: Model, identity: str, reality: list[dict], question: str, done=None) -> dict:
    """Stream messages to a model and return parsed JSON.

    When done is provided, it is called with the accumulated text after each chunk.
    If done returns True, streaming stops early and the accumulated text is parsed.
    """
    messages = []
    if identity:
        messages.append({"role": "system", "content": identity})
    messages.extend(reality)
    messages.append({"role": "user", "content": question})
    logger.debug("models.chat_json", {"model": model.name, "provider": model.provider, "messages": messages, "done": done})

    try:
        parts = []
        if is_local(model):
            gen = ollama.chat_json(model.url, model.name, messages)
        elif model.provider == "anthropic":
            gen = anthropic.chat_json(model.url, model.api_key, model.name, messages)
        else:
            gen = openai.chat_json(model.url, model.api_key, model.name, messages)

        async for chunk in gen:
            parts.append(chunk)
            if done and done("".join(parts)):
                break

        raw = strings.strip_tag("".join(parts), "think")
        return strings.extract_json(raw)
    except ollama.OllamaError as e:
        raise ModelError(f"Model returned an error: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except json.JSONDecodeError as e:
        raise ModelError("Model returned an invalid JSON response") from e
    except OSError as e:
        raise ModelError(f"Model returned an error: {e}") from e
