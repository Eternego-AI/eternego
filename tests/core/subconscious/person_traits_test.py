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
            await subconscious.person_traits(p, "Person: just give me the answer")

        ollama.assert_call(
            run=run,
            response={"message": {"content": "The person prefers concise responses."}},
        )

        content = paths.read(paths.person_traits(p.id))
        assert "concise" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_includes_existing_in_prompt():
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
        paths.save_as_string(paths.person_traits(p.id), "The person uses humor.")

        async def run(url):
            p.thinking.url = url
            await subconscious.person_traits(p, "Person: be brief")

        def validate(r):
            substring = "The person uses humor."
            text = r["body"]["messages"][0]["content"]
            assert substring in text, f"Expected '{substring}' in '{text[:200]}...'"

        ollama.assert_call(
            run=run,
            validate=validate,
            response={"message": {"content": "The person uses humor.\nThe person prefers brevity."}},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
