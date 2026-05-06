from application.platform.strings import extract_braces, to_json


async def test_it_parses_valid_json():
    result = to_json('{"key": "value"}')
    assert result == {"key": "value"}


async def test_it_returns_empty_dict_on_invalid_json():
    assert to_json("not json") == {}
    assert to_json("") == {}
    assert to_json("{broken") == {}


# ── extract_braces ───────────────────────────────────────────────────────────


def test_extract_braces_simple():
    assert extract_braces('{"a": 1}') == '{"a": 1}'


def test_extract_braces_with_surrounding_prose():
    assert extract_braces('Sure! Here it is: {"a": 1} and that is all.') == '{"a": 1}'


def test_extract_braces_with_code_fence():
    text = 'Reply:\n```json\n{"a": 1}\n```'
    assert extract_braces(text) == '{"a": 1}'


def test_extract_braces_returns_none_for_no_braces():
    assert extract_braces("hello world") is None


def test_extract_braces_returns_none_for_unparseable():
    assert extract_braces("{broken") is None


def test_extract_braces_handles_nested_object():
    text = '{"outer": {"inner": "value"}}'
    assert extract_braces(text) == text


def test_extract_braces_handles_braces_inside_strings():
    """A tool call whose `content` arg contains JSON-shaped text — naive
    brace counting matches the inner string's `{` against the wrong `}`,
    returning truncated garbage. raw_decode is string-aware."""
    text = '{"tools.filesystem.write": {"path": "/x", "content": "{\\"k\\": 1}"}}'
    parsed = extract_braces(text)
    assert parsed == text, f"expected full text, got: {parsed!r}"


def test_extract_braces_handles_escaped_quote_then_brace():
    text = '{"x": "she said \\"yes\\" then {wrote}"}'
    parsed = extract_braces(text)
    assert parsed == text


def test_extract_braces_skips_invalid_then_finds_valid():
    """If the first { begins something unparseable, advance and find the next."""
    text = '{this is not json} but here is one: {"a": 1}'
    assert extract_braces(text) == '{"a": 1}'


def test_extract_braces_returns_first_of_multiple():
    text = '{"first": 1} and then {"second": 2}'
    assert extract_braces(text) == '{"first": 1}'
