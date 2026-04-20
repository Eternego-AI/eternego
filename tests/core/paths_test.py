from application.platform.processes import on_separate_process_async


async def test_md_list_extracts_lines_under_section():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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
        os.environ["ETERNEGO_HOME"] = tmp
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


async def test_destinies_in_projects_recurring_forward_across_a_week():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        # Only the next file exists, for 2026-04-21. Asking about a later week
        # should still see the daily recurrence projected into that week.
        paths.save_destiny_entry("test-paths", "reminder", "2026-04-21 09:00", "morning check-in\nrecurrence: daily")
        # A one-off on 2026-04-26
        paths.save_destiny_entry("test-paths", "schedule", "2026-04-26 14:00", "dentist")

        # Query the week 2026-04-25 to 2026-04-27 — all three should show
        # (projected for daily, one-off for the dentist).
        results_25 = paths.destinies_in("test-paths", "2026-04-25")
        results_26 = paths.destinies_in("test-paths", "2026-04-26")
        results_27 = paths.destinies_in("test-paths", "2026-04-27")

        # Each day of the projected recurring event shows up on its day
        assert any("2026-04-25 09:00" in r and "morning check-in" in r and "recurring: daily" in r for r in results_25), results_25
        assert any("2026-04-26 09:00" in r and "recurring: daily" in r for r in results_26), results_26
        assert any("2026-04-27 09:00" in r and "recurring: daily" in r for r in results_27), results_27

        # The one-off on 2026-04-26 also shows (no recurrence tag)
        assert any("dentist" in r and "recurring" not in r for r in results_26), results_26

        # 2026-04-25 has no dentist
        assert not any("dentist" in r for r in results_25), results_25

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_destinies_in_month_query_shows_all_recurring_days():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        paths.save_destiny_entry("test-paths", "reminder", "2026-04-21 09:00", "morning check-in\nrecurrence: daily")

        results = paths.destinies_in("test-paths", "2026-04")
        # 2026-04-21 through 2026-04-30 — 10 projections (including the actual)
        assert len(results) == 10, f"Expected 10 entries, got {len(results)}: {results}"
        assert all("recurring: daily" in r for r in results)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_destinies_in_non_recurring_matches_only_its_day():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        paths.save_destiny_entry("test-paths", "schedule", "2026-04-21 14:00", "dentist")

        on_day = paths.destinies_in("test-paths", "2026-04-21")
        other_day = paths.destinies_in("test-paths", "2026-04-22")
        assert len(on_day) == 1
        assert "dentist" in on_day[0]
        assert "recurring" not in on_day[0]
        assert other_day == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_add_history_entry_creates_file():
    def isolated():
        import os
        import tempfile
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        filename = paths.add_history_entry("test-paths", "conversation", "hello\nworld")
        history_dir = paths.history("test-paths")
        assert (history_dir / filename).exists()
        assert "hello\nworld" in (history_dir / filename).read_text()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
