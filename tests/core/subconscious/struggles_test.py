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
        p = Persona(id="test-sub", name="Primus", thinking=Model(name="llama3", url="TBD"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        async def run(url):
            p.thinking.url = url
            await subconscious.struggles(p, "Person: I keep procrastinating")

        ollama.assert_call(
            run=run,
            response={"message": {"content": "The person struggles with procrastination."}},
        )

        content = paths.read(paths.struggles(p.id))
        assert "procrastination" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
