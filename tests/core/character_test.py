from application.platform.processes import on_separate_process_async


async def test_shape_starts_with_root_h1_and_includes_character():
    def isolated():
        import os
        import tempfile
        from application.core.brain.character import shape
        from application.core.data import Model, Persona
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        persona = Persona(
            id="test-char",
            name="Primus",
            thinking=Model(name="llama3", url="not required"),
            birthday="2026-01-15",
        )

        home = paths.home(persona.id)
        home.mkdir(parents=True)
        (home / "person.md").write_text("The person lives in Amsterdam.")
        (home / "persona-trait.md").write_text("Use Dutch idioms when possible.")

        result = shape(persona)

        assert result.startswith("# You are an Eternego Persona"), "character must start with root H1"
        assert "Primus" in result
        assert "2026-01-15" in result
        assert "Truth" in result, "truth value should appear"
        assert "Care" in result, "care value should appear"
        assert "Responsibility" in result, "responsibility value should appear"
        assert "Be honest" in result
        assert "## Who You Are" in result
        assert "## What Sustains and Threatens You" in result
        assert "## How You Act" in result
        assert "## Permissions" in result
        # character is purely about the persona's being — no person data here
        assert "Amsterdam" not in result
        assert "Dutch idioms" not in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_shape_includes_permissions_block_when_empty():
    def isolated():
        import os
        import tempfile
        from application.core.brain.character import shape
        from application.core.data import Model, Persona
        from application.core import paths

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        persona = Persona(
            id="test-empty",
            name="Primus",
            thinking=Model(name="llama3", url="not required"),
        )

        home = paths.home(persona.id)
        home.mkdir(parents=True)

        result = shape(persona)

        assert "## Permissions" in result
        assert "(none granted yet)" in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
