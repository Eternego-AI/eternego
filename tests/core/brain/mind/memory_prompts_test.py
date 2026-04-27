from application.platform.processes import on_separate_process_async


async def test_prompts_marks_only_the_last_entry_as_cache_point():
    """memory.prompts is what chat_json reads. It must mark exactly one
    cache_point — on the last prompt — so Anthropic's cache_control cap
    (4 blocks per request, system + messages combined) is never breached
    no matter how many messages are in memory."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt

            persona = Persona(
                id="test-persona",
                name="Tester",
                thinking=Model(name="llama3", url="not required"),
                base_model="llama3",
            )
            memory = Memory(persona)
            memory.remember(Message(content="a", prompt=Prompt(role="user", content="a")))
            memory.remember(Message(content="b", prompt=Prompt(role="assistant", content="b")))
            memory.remember(Message(content="c", prompt=Prompt(role="user", content="c")))
            memory.remember(Message(content="d", prompt=Prompt(role="assistant", content="d")))

            cache_flags = [p.cache_point for p in memory.prompts]
            assert cache_flags == [False, False, False, True], f"expected last prompt cached only, got {cache_flags!r}"
            assert sum(1 for f in cache_flags if f) == 1, "exactly one cache_point must appear"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_prompts_recomputes_cache_point_as_messages_grow():
    """Adding new messages must shift the cache_point to the new last — the
    prompts property is authoritative on every read, no stale flags carry
    over from prior snapshots."""
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt

            persona = Persona(
                id="test-persona",
                name="Tester",
                thinking=Model(name="llama3", url="not required"),
                base_model="llama3",
            )
            memory = Memory(persona)
            memory.remember(Message(content="one", prompt=Prompt(role="user", content="one")))
            memory.remember(Message(content="two", prompt=Prompt(role="assistant", content="two")))

            first = memory.prompts
            assert [p.cache_point for p in first] == [False, True]

            memory.remember(Message(content="three", prompt=Prompt(role="user", content="three")))
            memory.remember(Message(content="four", prompt=Prompt(role="assistant", content="four")))

            second = memory.prompts
            assert [p.cache_point for p in second] == [False, False, False, True], \
                f"cache_point should move to the new last on every read, got {[p.cache_point for p in second]!r}"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_prompts_empty_when_no_messages():
    def isolated():
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core.brain.memory import Memory
            from application.core.data import Model, Persona

            persona = Persona(
                id="test-persona",
                name="Tester",
                thinking=Model(name="llama3", url="not required"),
                base_model="llama3",
            )
            memory = Memory(persona)
            assert memory.prompts == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
