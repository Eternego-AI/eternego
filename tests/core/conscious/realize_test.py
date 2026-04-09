from application.platform.processes import on_separate_process_async


async def test_does_nothing_when_no_signals():
    def isolated():
        async def noop_thinking(): pass
        import os
        import asyncio
        import tempfile
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3", url="not required"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        memory = Memory(p, [TestMeaning(p)])
        asyncio.run(conscious.realize(memory, p, lambda: "You are Primus.", noop_thinking))
        assert len(memory.perceptions) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_routes_signal_to_new_impression():
    def isolated():
        async def noop_thinking(): pass
        import os
        import json
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3", url="TBD"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        memory = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)

        async def run(url):
            p.thinking.url = url
            await conscious.realize(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"routes": [{"signal": 1, "threads": [], "new_impressions": ["greeting"]}]}),
        )

        assert len(memory.perceptions) == 1
        assert memory.perceptions[0].impression == "greeting"
        assert len(memory.needs_realizing) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_routes_signal_to_existing_thread():
    def isolated():
        async def noop_thinking(): pass
        import os
        import json
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3", url="TBD"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        memory = Memory(p, [TestMeaning(p)])
        s1 = Signal(id="s1", event=SignalEvent.heard, content="hi", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s1)
        memory.realize(s1, "greeting")

        s2 = Signal(id="s2", event=SignalEvent.heard, content="how are you", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s2)

        async def run(url):
            p.thinking.url = url
            await conscious.realize(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"routes": [{"signal": 1, "threads": [1], "new_impressions": []}]}),
        )

        assert len(memory.perceptions) == 1
        assert len(memory.perceptions[0].thread) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_routes_signal_to_both_existing_and_new():
    def isolated():
        async def noop_thinking(): pass
        import os
        import json
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3", url="TBD"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        memory = Memory(p, [TestMeaning(p)])
        s1 = Signal(id="s1", event=SignalEvent.heard, content="existing topic", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s1)
        memory.realize(s1, "topic A")

        s2 = Signal(id="s2", event=SignalEvent.heard, content="mixed message", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s2)

        async def run(url):
            p.thinking.url = url
            await conscious.realize(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"routes": [{"signal": 1, "threads": [1], "new_impressions": ["topic B"]}]}),
        )

        assert len(memory.perceptions) == 2
        impressions = [p.impression for p in memory.perceptions]
        assert "topic A" in impressions
        assert "topic B" in impressions

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_skips_invalid_signal_number():
    def isolated():
        async def noop_thinking(): pass
        import os
        import json
        import tempfile
        from datetime import datetime
        from application.core.brain.mind import conscious
        from application.core.brain.mind.memory import Memory
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-conscious", name="Primus", thinking=Model(name="llama3", url="TBD"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        memory = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)

        async def run(url):
            p.thinking.url = url
            await conscious.realize(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"routes": [{"signal": 999, "threads": [], "new_impressions": ["x"]}]}),
        )

        assert len(memory.needs_realizing) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
