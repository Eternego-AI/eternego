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
        asyncio.run(conscious.conclude(memory, p, lambda: "You are Primus.", noop_say, noop_thinking))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_summarizes_with_model():
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
        memory.realize(s, "task")
        thought = memory.understand(memory.perceptions[0], TestMeaning(p))
        memory.answer(thought, "done", SignalEvent.recap)

        said = []

        async def capture_say(text):
            said.append(text)

        ollama.assert_call(
            run=lambda: conscious.conclude(memory, p, lambda: "You are Primus.", capture_say, noop_thinking),
            response={"message": {"content": "Task completed successfully."}},
        )

        assert said == ["Task completed successfully."]
        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.summarized

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_uses_recap_when_no_summarize():
    def isolated():
        async def noop_thinking(): pass
        import os
        import asyncio
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3"))

        class NoSummaryMeaning(Meaning):
            name = "NoSummary"
            def description(self): return "No summary meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return "Extract"
            def summarize(self): return None

        async def noop_say(text):
            pass

        memory = Memory(p, [NoSummaryMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "task")
        thought = memory.understand(memory.perceptions[0], NoSummaryMeaning(p))
        memory.answer(thought, "all done here", SignalEvent.recap)

        asyncio.run(conscious.conclude(memory, p, lambda: "You are Primus.", noop_say, noop_thinking))

        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.summarized
        assert last.content == "all done here"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
