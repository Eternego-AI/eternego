"""Models — call a model with an Action declaration; return parsed JSON.

`tool(model, prompts, question, action)` is the single JSON path for
every cognitive function. The caller declares what shape it expects
via an `Action` (see `core.data.Action`); `core.actions.translation`
converts that to each provider's tool-call shape. Platforms with
native tool support (Anthropic, OpenAI) get a schema-enforced call;
platforms without (xAI, Ollama) fall through to their JSON-mode flag
and rely on the prompt for shape.

The cognitive layer never speaks JSON Schema directly — it speaks
Action. Provider translation lives in one place.
"""

import json

from application.core import actions
from application.core.data import Action, Model, Prompt
from application.core.exceptions import EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, xai, strings

from .extract_json import extract_json
from .is_local import is_local


async def tool(model: Model, prompts: list[Prompt], question: str, action: Action, done=None) -> dict | None:
    """Stream a conversation to a model in tool mode; return parsed JSON or None.

    `prompts` is the conversation; `question` is appended as the final
    user turn. `action` declares the expected JSON shape.

    Returns:
    - `dict` — model produced a non-empty JSON object. Caller validates
      whatever fields it expects; missing fields are the model deliberately
      choosing not to address that area.
    - `None` — model returned `{}` (empty). Means "model gave up" / "no
      useful content this call." Distinct from missing-fields. Each caller
      decides what None means for them.
    - Raises `ModelError` — no JSON at all, or malformed JSON.

    `done(accumulated_text)` is optional. Without it, the stream auto-
    stops the moment the accumulated text parses as a complete root
    JSON object — saves tokens when a provider keeps generating after
    the answer.
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
    logger.debug("models.tool", {"model": model.name, "provider": model.provider, "messages": messages, "action": action.name, "done": done})

    tools, tool_choice = actions.translation(model.provider or "", action)

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
                if msg.pop("cache_point", False):
                    msg["cache_control"] = "ephemeral"
            gen = anthropic.chat_json(
                model.url, model.api_key, model.name, messages,
                tools=tools, tool_choice=tool_choice,
            )
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
            gen = xai.chat_json(model.url, model.api_key, model.name, messages)
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
            gen = openai.chat_json(
                model.url, model.api_key, model.name, messages,
                tools=tools, tool_choice=tool_choice,
            )

        decoder = json.JSONDecoder()
        async for chunk in gen:
            parts.append(chunk)
            accumulated = "".join(parts)
            if done:
                if done(accumulated):
                    break
            else:
                text = accumulated.lstrip()
                if text.startswith("{"):
                    try:
                        decoder.raw_decode(text)
                        break
                    except ValueError:
                        pass

        raw = strings.strip_tag("".join(parts), "think")
        parsed = extract_json(raw)
        return parsed if parsed else None
    except ollama.OllamaError as e:
        raise EngineConnectionError(f"Model service returned an error: {e}", model=model) from e
    except ConnectionError as e:
        raise EngineConnectionError(f"Could not reach model service: {e}", model=model) from e
    except OSError as e:
        raise EngineConnectionError(
            f"Model service returned an error: {e}",
            model=model,
            details=getattr(e, "details", None),
        ) from e
