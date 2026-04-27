from application.core.models.extract_json import extract_json
from application.core.exceptions import ModelError


async def test_it_extracts_json_from_prose():
    text = 'Here is the result: {"tool": "execute", "command": "ls"} hope that helps'
    result = extract_json(text)
    assert result == {"tool": "execute", "command": "ls"}


async def test_it_extracts_json_from_code_fences():
    text = '```json\n{"key": "value"}\n```'
    result = extract_json(text)
    assert result == {"key": "value"}


async def test_it_raises_when_no_json_found():
    try:
        extract_json("no json here")
        assert False, "should have raised"
    except ModelError:
        pass


async def test_it_handles_nested_json():
    text = 'result: {"outer": {"inner": [1, 2, 3]}}'
    result = extract_json(text)
    assert result == {"outer": {"inner": [1, 2, 3]}}


async def test_it_ignores_text_with_braces_after_json():
    text = '{"ability": 1}\nI chose this because the conversation involves general chat}'
    result = extract_json(text)
    assert result == {"ability": 1}


async def test_it_handles_json_followed_by_explanation():
    text = '```json\n{"tool": "say", "text": "Hello"}\n```\n\nI selected this tool because it is appropriate.'
    result = extract_json(text)
    assert result == {"tool": "say", "text": "Hello"}


async def test_it_handles_braces_inside_string_values():
    text = '{"text": "Use {name} as placeholder", "tool": "say"}'
    result = extract_json(text)
    assert result == {"text": "Use {name} as placeholder", "tool": "say"}


async def test_it_handles_escaped_quotes_in_strings():
    text = '{"text": "She said \\"hello\\" to me"}'
    result = extract_json(text)
    assert result == {"text": 'She said "hello" to me'}


async def test_it_extracts_first_json_when_multiple_present():
    text = '{"ability": 1}\n{"ability": 2}'
    result = extract_json(text)
    assert result == {"ability": 1}


async def test_it_handles_deeply_nested_objects():
    text = 'result: {"a": {"b": {"c": {"d": "deep"}}}}'
    result = extract_json(text)
    assert result == {"a": {"b": {"c": {"d": "deep"}}}}


async def test_it_raises_on_incomplete_json():
    try:
        extract_json('{"key": "value"')
        assert False, "should have raised"
    except ModelError:
        pass


async def test_it_handles_empty_object():
    result = extract_json("{}")
    assert result == {}


async def test_it_handles_newlines_and_whitespace_in_json():
    text = '```json\n{\n  "ability": 5\n    }\n```'
    result = extract_json(text)
    assert result == {"ability": 5}


async def test_it_handles_string_with_backslashes():
    text = r'{"path": "C:\\Users\\test\\file.txt"}'
    result = extract_json(text)
    assert result == {"path": "C:\\Users\\test\\file.txt"}
