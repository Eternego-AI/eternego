from application.platform.strings import to_json


async def test_it_parses_valid_json():
    result = to_json('{"key": "value"}')
    assert result == {"key": "value"}


async def test_it_returns_empty_dict_on_invalid_json():
    assert to_json("not json") == {}
    assert to_json("") == {}
    assert to_json("{broken") == {}
