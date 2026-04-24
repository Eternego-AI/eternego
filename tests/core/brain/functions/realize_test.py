from application.platform.processes import on_separate_process_async


async def test_cache_point_does_not_accumulate_across_ticks():
    """Realize marks the last message as a cache breakpoint each tick. Anthropic
    caps cache_control blocks at 4 per request (system + messages combined), so
    stale cache_points from earlier ticks must be cleared before the new one is
    set — otherwise they pile up and the API returns 400 after a few ticks."""
    def isolated():
        import asyncio
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.mind.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

            persona = Persona(
                id="test-persona",
                name="Tester",
                thinking=Model(name="llama3", url="not required"),
                base_model="llama3",
            )
            memory = Memory(persona)
            memory.remember(Message(content="one", prompt=Prompt(role="user", content="one")))
            memory.remember(Message(content="two", prompt=Prompt(role="assistant", content="two")))
            ego = agents.Ego(persona, FakeWorker())

            asyncio.run(functions.realize(ego, "identity", memory))
            messages = memory.messages
            flags_after_first = [m.prompt.cache_point for m in messages]
            assert flags_after_first == [False, True], f"first realize: {flags_after_first!r}"

            memory.remember(Message(content="three", prompt=Prompt(role="user", content="three")))
            memory.remember(Message(content="four", prompt=Prompt(role="assistant", content="four")))

            asyncio.run(functions.realize(ego, "identity", memory))
            flags_after_second = [m.prompt.cache_point for m in memory.messages]
            assert flags_after_second == [False, False, False, True], f"second realize: {flags_after_second!r}"
            assert sum(flags_after_second) == 1, "exactly one cache_point must survive each realize pass"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_cache_point_survives_prompts_property():
    """memory.prompts is what chat_json reads. The cache_point flag must come
    through on exactly the last prompt so the anthropic branch can translate
    it to cache_control."""
    def isolated():
        import asyncio
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            from application.core import agents
            from application.core.brain import functions
            from application.core.brain.mind.memory import Memory
            from application.core.data import Message, Model, Persona, Prompt

            class FakeWorker:
                def run(self, *a): pass
                def nudge(self): pass

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
            ego = agents.Ego(persona, FakeWorker())

            asyncio.run(functions.realize(ego, "identity", memory))
            prompts = memory.prompts
            cache_points = [p.get("cache_point") for p in prompts]
            assert cache_points == [None, None, True], f"expected last prompt cached only, got {cache_points!r}"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
