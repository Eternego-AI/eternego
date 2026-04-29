from application.platform.processes import on_separate_process_async


async def test_save_lesson_rejects_empty_intention():
    """A lesson without intention text has no id to slug from."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            try:
                save_lesson("test-persona", "", "some path text")
                assert False, "Expected ValueError for empty intention"
            except ValueError as e:
                assert "intention" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_lesson_rejects_empty_path():
    """A lesson with no body is nothing for the persona to translate."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            try:
                save_lesson("test-persona", "Reading the news", "")
                assert False, "Expected ValueError for empty path"
            except ValueError as e:
                assert "path" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_lesson_slugs_intention():
    """Intention 'Posting on X' becomes lesson_id 'posting_on_x'."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            lesson_id = save_lesson(
                "test-persona",
                "Posting on X",
                "Use the X API. Find your credentials in your past notes.",
            )
            assert lesson_id == "posting_on_x"

            lesson_path = tmp + "/personas/test-persona/home/lessons/posting_on_x.md"
            assert os.path.exists(lesson_path)
            with open(lesson_path) as f:
                content = f.read()
            assert content.startswith("# Posting on X")
            assert "Use the X API" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_lesson_strips_punctuation_in_id():
    """Punctuation in the intention is removed; underscores and dashes survive."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            lesson_id = save_lesson(
                "test-persona",
                "Researching: today's news!?",
                "Look it up.",
            )
            assert lesson_id == "researching_todays_news"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_save_lesson_rejects_unsluggable_intention():
    """Intention with no alphanumerics fails — nothing to use as id."""
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_lesson

            try:
                save_lesson("test-persona", "!!!", "path")
                assert False, "Expected ValueError for empty post-sanitization id"
            except ValueError as e:
                assert "id" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


