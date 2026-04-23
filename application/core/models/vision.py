"""Models — send an image with a question to a model and return the description."""

from pathlib import Path

from application.core.data import Model
from application.core.exceptions import EngineConnectionError
from application.platform import filesystem, logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def vision(model: Model, identity: str, source: Path, question: str) -> str:
    """Send an image with a question to a model and return the answer as text."""
    logger.debug("models.vision", {"model": model.name, "provider": model.provider, "source": str(source)})

    image_data = filesystem.read_base64(source)
    media_type = "image/png" if source.suffix.lower() == ".png" else "image/jpeg"

    messages = []
    if identity:
        messages.append({"role": "system", "content": identity})

    if is_local(model):
        messages.append({"role": "user", "content": question, "images": [image_data]})
        gen = ollama.chat(model.url, model.name, messages)
    elif model.provider == "anthropic":
        messages.append({"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
            {"type": "text", "text": question},
        ]})
        gen = anthropic.chat(model.url, model.api_key, model.name, messages)
    else:
        data_uri = f"data:{media_type};base64,{image_data}"
        messages.append({"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": data_uri}},
            {"type": "text", "text": question},
        ]})
        gen = openai.chat(model.url, model.api_key, model.name, messages)

    try:
        parts = []
        async for chunk in gen:
            parts.append(chunk)
        return strings.strip_tag("".join(parts), "think")
    except ollama.OllamaError as e:
        raise EngineConnectionError(f"Vision model returned an error: {e}", model=model) from e
    except ConnectionError as e:
        raise EngineConnectionError(f"Could not reach vision model: {e}", model=model) from e
    except OSError as e:
        raise EngineConnectionError(f"Vision model returned an error: {e}", model=model) from e
