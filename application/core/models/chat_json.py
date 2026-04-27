"""Models — send a conversation to a model and return parsed JSON."""

from application.core.data import Model, Prompt
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings

from .extract_json import extract_action, extract_json
from .is_local import is_local


async def chat_json(model: Model, prompts: list[Prompt], question: str, done=None) -> dict:
    """Stream a conversation to a model and return parsed JSON.

    `prompts` is the full conversation as a flat list of `Prompt` objects —
    system blocks, past user/assistant turns, anything the caller wants. The
    models layer does not care what is system and what is not; it reads
    `role` on each Prompt. `question` is appended as the final user turn.

    Providers are fed the same message list; system-role prompts are
    collected into the provider's system slot, cache_point flags translate
    to cache_control on Anthropic and are stripped elsewhere.

    Prompts whose content is a list of blocks (text + image) are carried
    through in anthropic-shaped form (that is what realize/decide produce
    when images are involved). For Ollama the images are extracted into the
    message's `images` field and the text is collapsed; for OpenAI the
    image blocks are rewritten to `image_url` form.

    When `done` is provided, it is called with the accumulated text after
    each chunk. If `done` returns True, streaming stops early and the
    accumulated text is parsed.
    """
    raw = await _chat_raw(model, prompts, question, done)
    return extract_json(raw)


async def chat_action(model: Model, prompts: list[Prompt], question: str, done=None) -> tuple[str, dict]:
    """Like chat_json, but also returns the prose surrounding the JSON action.

    Recognize and decide use this so a model writing natural-language voice
    alongside its JSON selector gets that voice honored — the prose becomes a
    say, the JSON action runs as normal."""
    raw = await _chat_raw(model, prompts, question, done)
    return extract_action(raw)


async def _chat_raw(model: Model, prompts: list[Prompt], question: str, done=None) -> str:
    """Build messages, stream the model, and return the joined raw text."""
    messages: list[dict] = []
    for p in prompts:
        if not p.content:
            continue
        entry = {"role": p.role, "content": p.content}
        if p.cache_point:
            entry["cache_point"] = True
        messages.append(entry)
    messages.append({"role": "user", "content": question})
    logger.debug("models.chat_json", {"model": model.name, "provider": model.provider, "messages": messages, "done": done})

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
            gen = ollama.chat_json(model.url, model.name, messages)
        elif model.provider == "anthropic":
            for msg in messages:
                if msg.get("role") == "system":
                    msg["cache_control"] = "ephemeral"
                elif msg.pop("cache_point", False):
                    msg["cache_control"] = "ephemeral"
            gen = anthropic.chat_json(model.url, model.api_key, model.name, messages)
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
            gen = openai.chat_json(model.url, model.api_key, model.name, messages)

        async for chunk in gen:
            parts.append(chunk)
            if done and done("".join(parts)):
                break

        return strings.strip_tag("".join(parts), "think")
    except ollama.OllamaError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
    except ConnectionError as e:
        raise EngineConnectionError(f"Could not reach model service: {e}", model=model) from e
    except OSError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
