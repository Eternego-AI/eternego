from application.platform.processes import on_separate_process_async


async def test_rejects_empty_intention():
    """A meaning without intention text fails fast — won't be matchable."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            try:
                save_meaning("test-persona", "broken", "", "some path text")
                assert False, "Expected ValueError for empty intention"
            except ValueError as e:
                assert "intention" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_rejects_empty_path():
    """A meaning without path text is no meaning at all."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            try:
                save_meaning("test-persona", "broken", "an intention", "")
                assert False, "Expected ValueError for empty path"
            except ValueError as e:
                assert "path" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_rejects_unsanitizable_name():
    """A name that becomes empty after sanitization is rejected."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            try:
                save_meaning("test-persona", "!!!", "intent", "path")
                assert False, "Expected ValueError for empty post-sanitization name"
            except ValueError as e:
                assert "name" in str(e).lower()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_accepts_valid_meaning():
    """A well-formed meaning is written to disk as .md and returns its sanitized name."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning, load
            from application.core.data import Model, Persona

            name = save_meaning(
                "test-persona",
                "reading_aloud",
                "Reading the content aloud",
                "Speak the content aloud at a steady pace, pausing on punctuation.",
            )
            assert name == "reading_aloud"

            meaning_file = tmp + "/personas/test-persona/home/meanings/reading_aloud.md"
            assert os.path.exists(meaning_file), "Valid meaning should be written to disk as .md"

            persona = Persona(id="test-persona", name="test", thinking=Model(name="m", url=""))
            loaded = load(persona, "reading_aloud")
            assert loaded is not None
            assert loaded.intention() == "Reading the content aloud"
            assert "Speak the content aloud" in loaded.path()

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_round_trip_through_md_format():
    """Saved + loaded meaning preserves intention and path verbatim, modulo trim."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning, load
            from application.core.data import Model, Persona

            intention = "Asking permission for a thing"
            path = "Paragraph one with detail.\n\nParagraph two with more.\n\n- a list item\n- another"
            name = save_meaning("test-persona", "asking_permission", intention, path)

            persona = Persona(id="test-persona", name="test", thinking=Model(name="m", url=""))
            loaded = load(persona, name)
            assert loaded is not None
            assert loaded.intention() == intention
            assert loaded.path() == path

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
