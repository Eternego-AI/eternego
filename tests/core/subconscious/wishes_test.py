from application.platform.processes import on_separate_process_async


async def test_writes_to_correct_file():
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

        ollama.assert_call(
            run=lambda: subconscious.wishes(p, "Person: I want to visit Japan"),
            response={"message": {"content": "The person wants to visit Japan."}},
        )

        content = paths.read(paths.wishes(p.id))
        assert "Japan" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
