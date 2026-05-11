from application.platform.processes import on_separate_process_async


async def test_save_lesson_rejects_empty_intention():
    """A lesson without intention text has nothing to anchor it."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            try:
                save_lesson("test-persona", "", "some body text")
                assert False, "Expected ValueError for empty intention"
            except ValueError as e:
                assert "intention" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_lesson_rejects_empty_body():
    """A lesson with no body is nothing for the persona to translate."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            try:
                save_lesson("test-persona", "Reading the news", "")
                assert False, "Expected ValueError for empty body"
            except ValueError as e:
                assert "body" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_lesson_writes_under_uuid():
    """save_lesson returns an opaque UUID and writes the file under that
    name. The filename is intentionally not derived from the intention —
    cognitive callers identify meanings by intention text, not filename."""
    def isolated():
        import os, re, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            file_id = save_lesson(
                "test-persona",
                "Posting on X",
                "Use the X API. Find your credentials in your past notes.",
            )
            # UUID4 shape: 8-4-4-4-12 hex
            assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", file_id), \
                f"expected UUID, got {file_id!r}"
            lesson_path = tmp + f"/personas/test-persona/home/lessons/{file_id}.md"
            assert os.path.exists(lesson_path)
            with open(lesson_path) as f:
                content = f.read()
            assert content.startswith("# Posting on X")
            assert "Use the X API" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_lesson_returns_unique_ids():
    """Two calls with the same intention return two different UUIDs and
    two different files. Same intention text doesn't collide on disk."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            id_a = save_lesson("test-persona", "Reading the news", "body a")
            id_b = save_lesson("test-persona", "Reading the news", "body b")
            assert id_a != id_b
            assert os.path.exists(tmp + f"/personas/test-persona/home/lessons/{id_a}.md")
            assert os.path.exists(tmp + f"/personas/test-persona/home/lessons/{id_b}.md")

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error




