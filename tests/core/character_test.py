from application.platform.processes import on_separate_process_async


async def test_shape_composes_full_character_prompt():
    def isolated():
        import os
        import tempfile
        from pathlib import Path
        from application.core.brain.character import shape
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        persona = Persona(
            id="test-char",
            name="Primus",
            model=Model(name="llama3"),
            birthday="2026-01-15",
        )

        home = Path(tmp) / ".eternego" / "personas" / persona.id / "home"
        home.mkdir(parents=True)
        (home / "person.md").write_text("The person lives in Amsterdam.\nThe person is a software engineer.")
        (home / "persona-trait.md").write_text("Be concise.\nUse humor when appropriate.")

        result = shape(persona)

        assert "Primus" in result
        assert "2026-01-15" in result
        assert "Integrity" in result
        assert "Speak plainly" in result
        assert "Amsterdam" in result
        assert "Be concise" in result
        assert "# Who You Are" in result
        assert "# The Person You Live With" in result
        assert "# Your Personality" in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_shape_omits_empty_identity_sections():
    def isolated():
        import os
        import tempfile
        from pathlib import Path
        from application.core.brain.character import shape
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        persona = Persona(
            id="test-empty",
            name="Primus",
            model=Model(name="llama3"),
        )

        home = Path(tmp) / ".eternego" / "personas" / persona.id / "home"
        home.mkdir(parents=True)
        (home / "person.md").write_text("")
        (home / "persona-trait.md").write_text("")

        result = shape(persona)

        assert "# Who You Are" in result
        assert "# The Person You Live With" not in result
        assert "# Your Personality" not in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
