from application.platform.processes import on_separate_process_async


async def test_md_list_extracts_lines_under_section():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        p = paths.home("test-paths")
        p.mkdir(parents=True, exist_ok=True)
        f = p / "test.md"
        f.write_text("## Tasks\nBuy milk\nCall dentist\n## Notes\nSomething else\n")
        result = paths.md_list(f, "Tasks")
        assert result == ["Buy milk", "Call dentist"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_md_list_returns_empty_for_missing_section():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        p = paths.home("test-paths")
        p.mkdir(parents=True, exist_ok=True)
        f = p / "test.md"
        f.write_text("## Other\nContent\n")
        result = paths.md_list(f, "Tasks")
        assert result == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_md_list_returns_empty_for_missing_file():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        result = paths.md_list(paths.home("test-paths") / "nonexistent.md", "Tasks")
        assert result == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_delete_entry_removes_matching_line():
    def isolated():
        import os
        import tempfile
        from application.core import paths
        from application.platform.crypto import generate_unique_id

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        p = paths.home("test-paths")
        p.mkdir(parents=True, exist_ok=True)
        f = p / "entries.md"
        f.write_text("first line\nsecond line\nthird line\n")
        hash_id = generate_unique_id("second line")
        paths.delete_entry(f, hash_id)
        content = f.read_text()
        assert "second line" not in content
        assert "first line" in content
        assert "third line" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_delete_entry_does_nothing_for_missing_hash():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        p = paths.home("test-paths")
        p.mkdir(parents=True, exist_ok=True)
        f = p / "entries.md"
        f.write_text("first line\nsecond line\n")
        paths.delete_entry(f, "nonexistent")
        content = f.read_text()
        assert "first line" in content
        assert "second line" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_due_destiny_entries_returns_entries_before_time():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        dest = paths.destiny("test-paths")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "reminder-2026-03-15-10-00-20260315090000.md").write_text("doctor appointment")
        (dest / "reminder-2026-03-15-14-00-20260315090000.md").write_text("team meeting")
        (dest / "reminder-2026-03-16-10-00-20260315090000.md").write_text("tomorrow task")

        before = datetime(2026, 3, 15, 12, 0)
        result = paths.due_destiny_entries("test-paths", before)
        assert len(result) == 1
        assert "doctor appointment" in result[0][1]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_due_destiny_entries_empty_when_none_due():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        dest = paths.destiny("test-paths")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "reminder-2026-03-20-10-00-20260315090000.md").write_text("future task")

        before = datetime(2026, 3, 15, 12, 0)
        result = paths.due_destiny_entries("test-paths", before)
        assert result == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_and_read_destiny_entry():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        paths.save_destiny_entry("test-paths", "reminder", "2026-03-15 10:00", "Call the dentist")
        dest = paths.destiny("test-paths")
        files = list(dest.glob("*.md"))
        assert len(files) == 1
        assert "Call the dentist" in files[0].read_text()
        assert "reminder" in files[0].name
        assert "2026-03-15" in files[0].name

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_read_files_matching():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        dest = paths.destiny("test-paths")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "note-2026-03-15.md").write_text("today's note")
        (dest / "note-2026-03-16.md").write_text("tomorrow's note")
        (dest / "other.txt").write_text("not a match")

        result = paths.read_files_matching("test-paths", dest, "*2026-03-15*")
        assert len(result) == 1
        assert "today's note" in result[0]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_add_history_entry_creates_file():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        filename = paths.add_history_entry("test-paths", "conversation", "hello\nworld")
        history_dir = paths.history("test-paths")
        assert (history_dir / filename).exists()
        assert "hello\nworld" in (history_dir / filename).read_text()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
