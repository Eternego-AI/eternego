"""Actions — provider-agnostic Action class + per-provider translation.

The Action class declares what JSON shape a cognitive function expects;
the `translation()` function turns it into (tools, tool_choice) the
platform layer can use directly. Anthropic and OpenAI get schemas;
xAI and Ollama get None,None and fall back to their JSON-mode flag.
"""

from application.core import actions
from application.core.data import Action


def test_leaf_string_to_schema():
    schema = actions.to_json_schema(Action(name="x", type="string"))
    assert schema == {"type": "string"}


def test_object_with_required_and_optional_fields():
    a = Action(
        name="thinking",
        fields=[
            Action(name="a", type="string", required=True),
            Action(name="b", type="string", required=False),
        ],
    )
    schema = actions.to_json_schema(a)
    assert schema["type"] == "object"
    assert schema["properties"] == {"a": {"type": "string"}, "b": {"type": "string"}}
    assert schema["required"] == ["a"]
    assert schema["additionalProperties"] is False


def test_object_with_no_required_drops_required_key():
    a = Action(name="thinking", fields=[Action(name="x", type="string")])
    schema = actions.to_json_schema(a)
    assert "required" not in schema


def test_empty_fields_object_is_closed_empty():
    """An object Action with no declared fields means 'only the empty
    object `{}` is valid' — strict-compatible. Used for zero-arg tools
    like `take_screenshot` where the wire is `{"tools.X": {}}`."""
    a = Action(name="item", type="object")
    schema = actions.to_json_schema(a)
    assert schema == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }, schema


def test_array_with_empty_object_items():
    """Array items that take no args produce a closed empty-object schema."""
    a = Action(
        name="decision",
        type="array",
        items=Action(name="item", type="object"),
    )
    schema = actions.to_json_schema(a)
    assert schema["type"] == "array"
    assert schema["items"] == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }, schema["items"]


def test_one_of_emits_anyOf_in_schema():
    """`one_of=True` on an Action translates to JSON Schema's `anyOf`
    (not `oneOf`). OpenAI strict mode rejects `oneOf` but accepts
    `anyOf`; both express the union for our purposes — the model only
    emits one variant, and each variant is closed (one required key,
    no additional properties)."""
    a = Action(
        name="deciding",
        one_of=True,
        fields=[
            Action(name="say", type="string"),
            Action(name="done", type="null"),
        ],
    )
    schema = actions.to_json_schema(a)
    assert "anyOf" in schema
    assert len(schema["anyOf"]) == 2
    assert schema["anyOf"][0]["required"] == ["say"]
    assert schema["anyOf"][1]["required"] == ["done"]


def test_array_with_object_items():
    a = Action(
        name="listing",
        type="array",
        items=Action(name="item", type="object",
                     fields=[Action(name="k", type="string", required=True)]),
    )
    schema = actions.to_json_schema(a)
    assert schema["type"] == "array"
    assert schema["items"]["type"] == "object"
    assert schema["items"]["required"] == ["k"]


def test_anthropic_translation_returns_tools_and_tool_choice():
    a = Action(name="thinking", description="something",
               fields=[Action(name="x", type="string", required=True)])
    tools, tool_choice = actions.translation("anthropic", a)
    assert tools == [{
        "name": "thinking",
        "description": "something",
        "input_schema": actions.to_json_schema(a),
    }]
    assert tool_choice == {"type": "tool", "name": "thinking"}


def test_openai_translation_wraps_as_function():
    a = Action(name="thinking", description="something",
               fields=[Action(name="x", type="string", required=True)])
    tools, tool_choice = actions.translation("openai", a)
    assert tools == [{
        "type": "function",
        "function": {
            "name": "thinking",
            "description": "something",
            "parameters": actions.to_json_schema(a),
            "strict": True,
        },
    }]
    assert tool_choice == {"type": "function", "function": {"name": "thinking"}}


def test_xai_translation_returns_none_pair():
    a = Action(name="thinking")
    tools, tool_choice = actions.translation("xai", a)
    assert tools is None
    assert tool_choice is None


def test_ollama_translation_returns_none_pair():
    a = Action(name="thinking")
    tools, tool_choice = actions.translation("ollama", a)
    assert tools is None
    assert tool_choice is None


def test_unknown_provider_returns_none_pair():
    a = Action(name="thinking")
    tools, tool_choice = actions.translation("", a)
    assert tools is None
    assert tool_choice is None
