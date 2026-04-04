from application.platform.processes import on_separate_process_async


async def test_load_creates_empty_storage():
    def isolated():
        import tempfile
        from pathlib import Path
        from application.platform.persistent_memory import _cache, load, read

        _cache.clear()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            load("test", path)
            assert read("test") == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_load_reads_existing_file():
    def isolated():
        import tempfile
        from pathlib import Path
        from application.platform.persistent_memory import _cache, load, read

        _cache.clear()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            path.write_text('[{"name": "alice"}]')
            load("test", path)
            assert read("test") == [{"name": "alice"}]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_append_adds_and_persists():
    def isolated():
        import json
        import tempfile
        from pathlib import Path
        from application.platform.persistent_memory import _cache, load, append, read

        _cache.clear()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            load("test", path)
            append("test", {"name": "bob"})
            assert len(read("test")) == 1
            persisted = json.loads(path.read_text())
            assert persisted[0]["name"] == "bob"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_filter_by_returns_matching_items():
    def isolated():
        import tempfile
        from pathlib import Path
        from application.platform.persistent_memory import _cache, load, append, filter_by

        _cache.clear()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            load("test", path)
            append("test", {"type": "a", "value": 1})
            append("test", {"type": "b", "value": 2})
            append("test", {"type": "a", "value": 3})
            result = filter_by("test", lambda item: item["type"] == "a")
            assert len(result) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_remove_where_deletes_matching():
    def isolated():
        import tempfile
        from pathlib import Path
        from application.platform.persistent_memory import _cache, load, append, read, remove_where

        _cache.clear()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            load("test", path)
            append("test", {"keep": True})
            append("test", {"keep": False})
            remove_where("test", lambda item: not item["keep"])
            assert len(read("test")) == 1
            assert read("test")[0]["keep"] is True

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_clear_empties_storage():
    def isolated():
        import tempfile
        from pathlib import Path
        from application.platform.persistent_memory import _cache, load, append, read, clear

        _cache.clear()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            load("test", path)
            append("test", {"data": 1})
            clear("test")
            assert read("test") == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_verify_checks_content_hash():
    def isolated():
        import tempfile
        from pathlib import Path
        from application.platform.persistent_memory import _cache, load, append, verify

        _cache.clear()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            h = load("test", path)
            assert verify("test", h)
            append("test", {"change": True})
            assert not verify("test", h)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
