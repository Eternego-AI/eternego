from application.platform.processes import on_separate_process_async


async def test_rejects_path_returning_tuple():
    """A trailing-comma bug turns path() into a tuple. compile() accepts it;
    validation must catch it before the file lands on disk — otherwise decide
    crashes on 'str + tuple' three days later."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            code = "\n".join([
                '"""Meaning — ending_conversation."""',
                'from application.core.data import Persona',
                'class Meaning:',
                '    def __init__(self, persona: Persona):',
                '        self.persona = persona',
                '    def intention(self) -> str:',
                '        return "ending_conversation"',
                '    def path(self) -> str:',
                '        return "first section",',
                '        "second section"',
            ])
            try:
                save_meaning("test-persona", "ending_conversation", code)
                assert False, "Expected ValueError for tuple-returning path()"
            except ValueError as e:
                message = str(e)
                assert "path" in message and "tuple" in message, f"Unexpected message: {message}"
            meaning_file = tmp + "/personas/test-persona/home/meanings/ending_conversation.py"
            assert not os.path.exists(meaning_file), "Broken meaning should not be written to disk"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_rejects_missing_meaning_class():
    """A module without a Meaning class is not a meaning."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            code = "def some_function():\n    return 'hello'\n"
            try:
                save_meaning("test-persona", "broken", code)
                assert False, "Expected ValueError for missing Meaning class"
            except ValueError as e:
                assert "Meaning" in str(e), f"Unexpected message: {e}"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_rejects_syntax_error():
    """Syntactically invalid code is rejected by compile() — the pre-existing check."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            try:
                save_meaning("test-persona", "broken", "def foo(\n")
                assert False, "Expected SyntaxError"
            except SyntaxError:
                pass

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_rejects_runtime_errors_during_validation():
    """If exec, instantiation, or a method call raises anything, the meaning is
    rejected as a ValueError — learn catches (SyntaxError, ValueError), so
    execution failures must land in the ValueError channel or they'd escape."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            code = "\n".join([
                'from application.core.data import Persona',
                'class Meaning:',
                '    def __init__(self, persona: Persona):',
                '        self.persona = persona',
                '    def intention(self) -> str:',
                '        return undefined_name',
                '    def path(self) -> str:',
                '        return "ok"',
            ])
            try:
                save_meaning("test-persona", "broken", code)
                assert False, "Expected ValueError"
            except ValueError as e:
                assert "NameError" in str(e), f"Unexpected message: {e}"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_accepts_valid_meaning():
    """A well-formed meaning is written to disk and returns its sanitized name."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.meanings import save_meaning

            code = "\n".join([
                '"""Meaning — reading_aloud."""',
                'from application.core.data import Persona',
                'class Meaning:',
                '    def __init__(self, persona: Persona):',
                '        self.persona = persona',
                '    def intention(self) -> str:',
                '        return "reading_aloud"',
                '    def path(self) -> str:',
                '        return "speak the content aloud"',
            ])
            name = save_meaning("test-persona", "reading_aloud", code)
            assert name == "reading_aloud"
            meaning_file = tmp + "/personas/test-persona/home/meanings/reading_aloud.py"
            assert os.path.exists(meaning_file), "Valid meaning should be written to disk"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
