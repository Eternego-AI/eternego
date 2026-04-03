from application.platform.lists import filter_by, as_list


async def test_it_filters_by_predicate():
    result = filter_by([1, 2, 3, 4, 5], lambda x: x > 3)
    assert result == [4, 5]


async def test_it_returns_empty_list_when_nothing_matches():
    result = filter_by([1, 2, 3], lambda x: x > 10)
    assert result == []


async def test_it_handles_empty_list():
    result = filter_by([], lambda x: True)
    assert result == []


async def test_it_wraps_string_as_list():
    assert as_list("hello") == ["hello"]


async def test_it_returns_list_as_is():
    assert as_list([1, 2]) == [1, 2]


async def test_it_returns_empty_list_for_none():
    assert as_list(None) == []


async def test_it_returns_empty_list_for_empty_string():
    assert as_list("") == []
