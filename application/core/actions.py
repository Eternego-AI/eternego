"""Actions — translate an Action declaration to a provider's tool-call shape.

`Action` (in `core.data`) is Eternego's provider-agnostic way to declare
the JSON shape a cognitive function expects from the model. This module
turns an Action into the (tools, tool_choice) pair each provider's
chat_json takes.

Providers that don't support native tool calls (xAI today because of
chat-template leak; Ollama because the API doesn't offer it) return
`(None, None)` and rely on `response_format` / `format: "json"` plus
the prompt to carry shape.
"""

from application.core.data import Action


def to_json_schema(action: Action) -> dict:
    """Recursively convert an Action into a JSON Schema fragment.

    Used as the `input_schema` (Anthropic) or `parameters` (OpenAI) of
    the wrapped tool definition.
    """
    if action.type == "object":
        if action.one_of:
            # OpenAI strict mode rejects `oneOf` but accepts `anyOf`. Both
            # work for our case — the model emits one variant. We use
            # anyOf for compatibility; the "exactly one" semantic is
            # enforced by each variant requiring its own single key
            # and forbidding additional properties.
            schema: dict = {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {f.name: to_json_schema(f)},
                        "required": [f.name],
                        "additionalProperties": False,
                    }
                    for f in action.fields
                ],
            }
        elif action.fields:
            properties = {f.name: to_json_schema(f) for f in action.fields}
            required = [f.name for f in action.fields if f.required]
            schema = {
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            }
            if required:
                schema["required"] = required
        else:
            # No declared fields → object with no properties allowed.
            # This is what we emit for zero-arg tools (e.g.
            # `take_screenshot`) — wire format is `{"tools.X": {}}` and
            # the args object is exactly the empty object. Strict-mode
            # compatible.
            schema = {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }
        if action.description:
            schema["description"] = action.description
        return schema

    if action.type == "array":
        schema = {"type": "array"}
        if action.items is not None:
            schema["items"] = to_json_schema(action.items)
        if action.description:
            schema["description"] = action.description
        return schema

    schema = {"type": action.type}
    if action.description:
        schema["description"] = action.description
    return schema


def translation(provider: str, action: Action) -> tuple[list[dict] | None, dict | None]:
    """Return (tools, tool_choice) for the given provider, or (None, None)
    when the provider doesn't support tool calls cleanly.

    Anthropic: passes its native `{name, description, input_schema}`
    shape with `tool_choice: {type: "tool", name}` forcing the call.

    OpenAI: wraps to `{type: "function", function: {name, description,
    parameters}}` with `tool_choice: {type: "function", function:
    {name}}`.

    xAI: returns (None, None). Its function-calling implementation
    leaks chat-template tokens into the content stream; we fall back
    to `response_format: json_object` until they fix it.

    Ollama: returns (None, None). No native function calling on the
    /api/chat endpoint; uses `format: "json"` and lets the prompt
    carry shape.
    """
    if provider == "anthropic":
        return (
            [{
                "name": action.name,
                "description": action.description,
                "input_schema": to_json_schema(action),
            }],
            {"type": "tool", "name": action.name},
        )

    if provider == "openai":
        return (
            [{
                "type": "function",
                "function": {
                    "name": action.name,
                    "description": action.description,
                    "parameters": to_json_schema(action),
                    "strict": True,
                },
            }],
            {"type": "function", "function": {"name": action.name}},
        )

    return (None, None)
