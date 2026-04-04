from application.platform.processes import on_separate_process_async


# ── person_identity ──────────────────────────────────────────────────────────

async def test_person_identity_writes_model_response_to_file():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        ollama.assert_call(
            run=lambda: subconscious.person_identity(p, "Person: I live in Amsterdam"),
            response={"message": {"content": "The person lives in Amsterdam."}},
        )

        content = paths.read(paths.person_identity(p.id))
        assert "Amsterdam" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_person_identity_includes_existing_facts_in_prompt():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
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


async def test_person_identity_sends_conversation_as_user_message():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
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


# ── person_traits ────────────────────────────────────────────────────────────

async def test_person_traits_writes_to_correct_file():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        ollama.assert_call(
            run=lambda: subconscious.person_traits(p, "Person: just give me the answer"),
            response={"message": {"content": "The person prefers concise responses."}},
        )

        content = paths.read(paths.person_traits(p.id))
        assert "concise" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_person_traits_includes_existing_in_prompt():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)
        paths.save_as_string(paths.person_traits(p.id), "The person uses humor.")

        def assert_in(substring, text):
            assert substring in text, f"Expected '{substring}' in '{text[:200]}...'"

        ollama.assert_call(
            run=lambda: subconscious.person_traits(p, "Person: be brief"),
            validate=lambda r: assert_in("The person uses humor.", r["body"]["messages"][0]["content"]),
            response={"message": {"content": "The person uses humor.\nThe person prefers brevity."}},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── wishes ───────────────────────────────────────────────────────────────────

async def test_wishes_writes_to_correct_file():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        ollama.assert_call(
            run=lambda: subconscious.wishes(p, "Person: I want to visit Japan"),
            response={"message": {"content": "The person wants to visit Japan."}},
        )

        content = paths.read(paths.wishes(p.id))
        assert "Japan" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── struggles ────────────────────────────────────────────────────────────────

async def test_struggles_writes_to_correct_file():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        ollama.assert_call(
            run=lambda: subconscious.struggles(p, "Person: I keep procrastinating"),
            response={"message": {"content": "The person struggles with procrastination."}},
        )

        content = paths.read(paths.struggles(p.id))
        assert "procrastination" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── persona_trait ────────────────────────────────────────────────────────────

async def test_persona_trait_writes_to_correct_file():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        ollama.assert_call(
            run=lambda: subconscious.persona_trait(p, "Person: don't give me filler"),
            response={"message": {"content": "Be concise and direct."}},
        )

        content = paths.read(paths.persona_trait(p.id))
        assert "concise" in content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_persona_trait_includes_person_traits_in_prompt():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
        paths.home(p.id).mkdir(parents=True, exist_ok=True)
        paths.save_as_string(paths.person_traits(p.id), "The person is direct and technical.")

        def assert_in(substring, text):
            assert substring in text, f"Expected '{substring}' in '{text[:200]}...'"

        ollama.assert_call(
            run=lambda: subconscious.persona_trait(p, "Person: use DDD"),
            validate=lambda r: assert_in("The person is direct and technical.", r["body"]["messages"][0]["content"]),
            response={"message": {"content": "Be direct.\nUse DDD terminology."}},
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── synthesize_dna ───────────────────────────────────────────────────────────

async def test_synthesize_dna_writes_to_dna_file():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
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


async def test_synthesize_dna_includes_previous_dna_and_traits_in_prompt():
    def isolated():
        import os
        import tempfile
        from application.core.brain.mind import subconscious
        from application.core import paths
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-sub", name="Primus", model=Model(name="llama3"))
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
