"""Models — send a conversation to a model and return text."""

from application.core.data import Model, Prompt
from application.core.exceptions import EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .is_local import is_local


async def chat(model: Model, prompts: list[Prompt], question: str) -> str:
    """Stream a conversation to a model and return the complete response text.

    `prompts` is the full conversation as a flat list of `Prompt` objects;
    `question` is appended as the final user turn. See `chat_json` for the
    per-provider serialization contract, including how image content blocks
    are translated per provider."""
    messages: list[dict] = []
    for p in prompts:
        if not p.content:
            continue
        entry = {"role": p.role, "content": p.content}
        if p.cache_point:
            entry["cache_point"] = True
        messages.append(entry)
    messages.append({"role": "user", "content": question})
    logger.debug("models.chat", {"model": model.name, "provider": model.provider, "messages": messages})

    try:
        parts = []
        if is_local(model):
            for msg in messages:
                msg.pop("cache_point", None)
                if isinstance(msg["content"], list):
                    images = []
                    text_parts = []
                    for block in msg["content"]:
                        if block.get("type") == "image":
                            data = block.get("source", {}).get("data", "")
                            if data:
                                images.append(data)
                        elif block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    msg["content"] = "\n".join(text_parts)
                    if images:
                        msg["images"] = images
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
            for msg in messages:
                msg.pop("cache_point", None)
                if isinstance(msg["content"], list):
                    new_content = []
                    for block in msg["content"]:
                        if block.get("type") == "image":
                            source = block.get("source", {})
                            media_type = source.get("media_type", "image/jpeg")
                            data = source.get("data", "")
                            new_content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{data}"},
                            })
                        else:
                            new_content.append(block)
                    msg["content"] = new_content
            async for chunk in openai.chat(model.url, model.api_key, model.name, messages):
                parts.append(chunk)
        return strings.strip_tag("".join(parts), "think")
    except ollama.OllamaError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
    except ConnectionError as e:
        raise EngineConnectionError(f"Could not reach model service: {e}", model=model) from e
    except OSError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
