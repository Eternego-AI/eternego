from application.platform.processes import on_separate_process_async


async def test_writes_model_response_to_file():
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
            run=lambda: subconscious.person_identity(p, "Person: I live in Amsterdam"),
            response={"message": {"content": "The person lives in Amsterdam."}},
        )

        content = paths.read(paths.person_identity(p.id))
        assert "Amsterdam" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_includes_existing_facts_in_prompt():
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
        paths.save_as_string(paths.person_identity(p.id), "The person is a developer.")

        def assert_in(substring, text):
            assert substring in text, f"Expected '{substring}' in '{text[:200]}...'"

        ollama.assert_call(
            run=lambda: subconscious.person_identity(p, "Person: I moved to Paris"),
            validate=lambda r: assert_in("The person is a developer.", r["body"]["messages"][0]["content"]),
            response={"message": {"content": "The person is a developer.\nThe person lives in Paris."}},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_sends_conversation_as_user_message():
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

        def assert_in(substring, text):
            assert substring in text, f"Expected '{substring}' in '{text[:200]}...'"

        def assert_equal(actual, expected):
            assert actual == expected, f"Expected {expected}, got {actual}"

        ollama.assert_call(
            run=lambda: subconscious.person_identity(p, "Person: My name is Morteza"),
            validate=lambda r: (
                assert_equal(r["body"]["messages"][1]["role"], "user"),
                assert_in("Morteza", r["body"]["messages"][1]["content"]),
            ),
            response={"message": {"content": "The person's name is Morteza."}},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
