from application.platform.processes import on_separate_process_async


async def test_writes_to_dna_file():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", thinking=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)
        paths.save_as_string(paths.persona_trait(p.id), "Be concise.\nUse humor.")

        ollama.assert_call(
            run=lambda: subconscious.synthesize_dna(p),
            response={"message": {"content": "# Communication Style\n**Be concise**\nUse humor"}},
        )

        content = paths.read(paths.dna(p.id))
        assert "concise" in content
        assert "humor" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_includes_previous_dna_and_traits_in_prompt():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", thinking=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)
        paths.save_as_string(paths.dna(p.id), "Previous profile content")
        paths.save_as_string(paths.persona_trait(p.id), "Be direct.")

        def assert_in(substring, text):
            assert substring in text, f"Expected '{substring}' in '{text[:200]}...'"

        ollama.assert_call(
            run=lambda: subconscious.synthesize_dna(p),
            validate=lambda r: (
                assert_in("Previous profile content", r["body"]["messages"][0]["content"]),
                assert_in("Be direct.", r["body"]["messages"][0]["content"]),
            ),
            response={"message": {"content": "# Updated profile"}},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
