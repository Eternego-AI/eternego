from dataclasses import dataclass
from pathlib import Path

from application.platform.objects import Data, safe, json, are_equal, sensitive, hidden


@dataclass
class User(Data):
    name: str
    password: str = sensitive()
    bus: object = hidden()


def test_safe_masks_sensitive_fields():
    user = User(name="alice", password="secret123", bus="internal")
    result = safe(user)
    assert result["name"] == "alice"
    assert result["password"] == "***"


def test_safe_excludes_hidden_fields():
    user = User(name="alice", password="secret123", bus="internal")
    result = safe(user)
    assert "bus" not in result


def test_safe_shows_empty_string_for_none_sensitive():
    user = User(name="alice", password=None, bus=None)
    result = safe(user)
    assert result["password"] == ""


def test_json_includes_sensitive_values():
    user = User(name="alice", password="secret123", bus="internal")
    result = json(user)
    assert result["password"] == "secret123"


def test_json_excludes_hidden_fields():
    user = User(name="alice", password="secret123", bus="internal")
    result = json(user)
    assert "bus" not in result


def test_safe_handles_nested_data():
    @dataclass
    class Wrapper(Data):
        user: User

    w = Wrapper(user=User(name="bob", password="pass", bus=None))
    result = safe(w)
    assert result["user"]["name"] == "bob"
    assert result["user"]["password"] == "***"


def test_safe_handles_lists_and_dicts():
    result = safe({"items": [1, "two", None, True]})
    assert result == {"items": [1, "two", None, True]}


def test_safe_converts_path_to_string():
    from application.core import paths
    p = paths.home("test-id") / "context.md"
    result = safe(p)
    assert isinstance(result, str)
    assert "test-id" in result
    assert "context.md" in result


def test_are_equal_compares_by_serialized_form():
    a = User(name="alice", password="x", bus="a")
    b = User(name="alice", password="x", bus="b")
    assert are_equal(a, b)  # bus is hidden, excluded from comparison


def test_are_equal_detects_differences():
    a = User(name="alice", password="x", bus=None)
    b = User(name="bob", password="x", bus=None)
    assert not are_equal(a, b)
