from application.platform.processes import on_separate_process_async


async def test_does_nothing_when_no_thoughts():
    def isolated():
        async def noop_thinking(): pass
        import os
        import asyncio
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        async def noop_say(text):
            pass

        memory = Memory(p, [TestMeaning(p)])
        asyncio.run(conscious.acknowledge(memory, p, lambda: "You are Primus.", noop_say, noop_thinking))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_replies_on_heard_signal():
    def isolated():
        async def noop_thinking(): pass
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        memory = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "greeting")
        memory.understand(memory.perceptions[0], TestMeaning(p))

        said = []

        async def capture_say(text):
            said.append(text)

        ollama.assert_call(
            run=lambda: conscious.acknowledge(memory, p, lambda: "You are Primus.", capture_say, noop_thinking),
            response={"message": {"content": "Hello there!"}},
        )

        assert said == ["Hello there!"]
        last = memory.intentions[0].perception.thread[-1]
        assert last.event == SignalEvent.answered
        assert last.content == "Hello there!"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_uses_clarify_after_executed_signal():
    def isolated():
        async def noop_thinking(): pass
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        async def noop_say(text):
            pass

        memory = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "task")
        thought = memory.understand(memory.perceptions[0], TestMeaning(p))
        memory.inform(thought, Signal(id="exec1", event=SignalEvent.executed, content="Error: failed"))

        ollama.assert_call(
            run=lambda: conscious.acknowledge(memory, p, lambda: "You are Primus.", noop_say, noop_thinking),
            response={"message": {"content": "Let me try again"}},
        )

        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.clarified

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_forgets_thought_when_no_path():
    def isolated():
        async def noop_thinking(): pass
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3"))

        class NoPathMeaning(Meaning):
            name = "NoPath"
            def description(self): return "No path meaning"
            def clarify(self): return None
            def reply(self): return "Reply prompt"
            def path(self): return None
            def summarize(self): return None

        async def noop_say(text):
            pass

        memory = Memory(p, [NoPathMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "greeting")
        memory.understand(memory.perceptions[0], NoPathMeaning(p))

        ollama.assert_call(
            run=lambda: conscious.acknowledge(memory, p, lambda: "You are Primus.", noop_say, noop_thinking),
            response={"message": {"content": "Hi!"}},
        )

        assert len(memory.intentions) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
