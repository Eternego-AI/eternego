import json

from application.platform.strings import to_json, extract_json


def test_it_parses_valid_json():
    result = to_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_it_returns_empty_dict_on_invalid_json():
    assert to_json("not json") == {}
    assert to_json("") == {}
    assert to_json("{broken") == {}


def test_it_extracts_json_from_prose():
    text = 'Here is the result: {"tool": "execute", "command": "ls"} hope that helps'
    result = extract_json(text)
    assert result == {"tool": "execute", "command": "ls"}


def test_it_extracts_json_from_code_fences():
    text = '```json\n{"key": "value"}\n```'
    result = extract_json(text)
    assert result == {"key": "value"}


def test_it_raises_when_no_json_found():
    try:
        extract_json("no json here")
        assert False, "should have raised"
    except json.JSONDecodeError:
        pass


def test_it_handles_nested_json():
    text = 'result: {"outer": {"inner": [1, 2, 3]}}'
    result = extract_json(text)
    assert result == {"outer": {"inner": [1, 2, 3]}}
