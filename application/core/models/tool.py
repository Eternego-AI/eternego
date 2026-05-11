"""Models — call a model in structured mode and return parsed JSON.

`tool(model, prompts, question)` is the strict path: send the conversation
to the model, expect JSON back, return the parsed dict. If the model
returns anything that doesn't parse as JSON, raise `ModelError`. No
prose fallback, no salvage — cognitive callers either get a dict or a
failure they can handle.

Provider dispatch routes to each platform module's `tool()`, which uses
the provider's native structured-output mechanism:

- Ollama → `format: "json"`
- OpenAI / xAI → `response_format: {"type": "json_object"}`
- Anthropic → no native constraint yet (caller relies on prompt
  compliance; smaller Anthropic models may fail this contract — Sonnet/
  Opus comply, Haiku does not until provider-native tool_use lands)
"""

from application.core.data import Model, Prompt
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, xai, strings

from .extract_json import extract_json
from .is_local import is_local


async def tool(model: Model, prompts: list[Prompt], question: str, done=None) -> dict:
    """Stream a conversation to a model in structured mode; return parsed JSON.

    `prompts` is the full conversation as a flat list of `Prompt` objects —
    system blocks, past user/assistant turns, anything the caller wants. The
    models layer does not care what is system and what is not; it reads
    `role` on each Prompt. `question` is appended as the final user turn.

    Providers are fed the same message list; system-role prompts are
    collected into the provider's system slot, cache_point flags translate
    to cache_control on Anthropic and are stripped elsewhere.

    Prompts whose content is a list of blocks (text + image) are carried
    through in anthropic-shaped form. For Ollama the images are extracted
    into the message's `images` field and the text is collapsed; for OpenAI
    the image blocks are rewritten to `image_url` form.

    When `done` is provided, it is called with the accumulated text after
    each chunk. If `done` returns True, streaming stops early and the
    accumulated text is parsed.

    Raises `ModelError` if the response is not valid JSON.
    """
    messages: list[dict] = []
    for p in prompts:
        if not p.content:
            continue
        entry = {"role": p.role, "content": p.content}
        if p.cache_point:
            entry["cache_point"] = True
        messages.append(entry)
    messages.append({"role": "user", "content": question})
    logger.debug("models.tool", {"model": model.name, "provider": model.provider, "messages": messages, "done": done})

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
            gen = ollama.tool(model.url, model.name, messages)
        elif model.provider == "anthropic":
            for msg in messages:
                if msg.get("role") == "system":
                    msg["cache_control"] = "ephemeral"
                elif msg.pop("cache_point", False):
                    msg["cache_control"] = "ephemeral"
            gen = anthropic.tool(model.url, model.api_key, model.name, messages)
        elif model.provider == "xai":
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
            gen = xai.tool(model.url, model.api_key, model.name, messages)
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
            gen = openai.tool(model.url, model.api_key, model.name, messages)

        async for chunk in gen:
            parts.append(chunk)
            if done and done("".join(parts)):
                break

        raw = strings.strip_tag("".join(parts), "think")
        return extract_json(raw)
    except ollama.OllamaError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
    except ConnectionError as e:
        raise EngineConnectionError(f"Could not reach model service: {e}", model=model) from e
    except OSError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
