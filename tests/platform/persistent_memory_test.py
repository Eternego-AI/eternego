import tempfile
from pathlib import Path

from application.platform.persistent_memory import (
    _cache,
    load,
    append,
    read,
    filter_by,
    remove_where,
    clear,
    verify,
)


def _reset():
    _cache.clear()


def test_load_creates_empty_storage():
    _reset()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "store.json"
        load("test", path)
        assert read("test") == []
    _reset()


def test_load_reads_existing_file():
    _reset()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "store.json"
        path.write_text('[{"name": "alice"}]')
        load("test", path)
        assert read("test") == [{"name": "alice"}]
    _reset()


def test_append_adds_and_persists():
    _reset()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "store.json"
        load("test", path)
        append("test", {"name": "bob"})
        assert len(read("test")) == 1

        # Verify persisted to disk
        import json
        persisted = json.loads(path.read_text())
        assert persisted[0]["name"] == "bob"
    _reset()


def test_filter_by_returns_matching_items():
    _reset()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "store.json"
        load("test", path)
        append("test", {"type": "a", "value": 1})
        append("test", {"type": "b", "value": 2})
        append("test", {"type": "a", "value": 3})
        result = filter_by("test", lambda item: item["type"] == "a")
        assert len(result) == 2
    _reset()


def test_remove_where_deletes_matching():
    _reset()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "store.json"
        load("test", path)
        append("test", {"keep": True})
        append("test", {"keep": False})
        remove_where("test", lambda item: not item["keep"])
        assert len(read("test")) == 1
        assert read("test")[0]["keep"] is True
    _reset()


def test_clear_empties_storage():
    _reset()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "store.json"
        load("test", path)
        append("test", {"data": 1})
        clear("test")
        assert read("test") == []
    _reset()


def test_verify_checks_content_hash():
    _reset()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "store.json"
        h = load("test", path)
        assert verify("test", h)
        append("test", {"change": True})
        assert not verify("test", h)
    _reset()
