from application.platform.processes import on_separate_process_async


async def test_does_nothing_when_no_perceptions():
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

        async def noop_escalate(thread_text, meanings):
            return None

        memory = Memory(p, [TestMeaning(p)])
        asyncio.run(conscious.understand(memory, p, [TestMeaning(p)], lambda: "You are Primus.", noop_escalate, noop_thinking))
        assert len(memory.intentions) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_picks_meaning_by_row():
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

        class EscalationMeaning(Meaning):
            name = "Escalation"
            def description(self): return "Escalation"
            def clarify(self): return None
            def reply(self): return "I'll figure this out"
            def path(self): return None
            def summarize(self): return None

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        async def noop_escalate(thread_text, meanings):
            return None

        meanings = [TestMeaning(p), EscalationMeaning(p)]
        memory = Memory(p, meanings)
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "greeting")

        async def run(url):
            p.thinking.url = url
            await conscious.understand(memory, p, meanings, lambda: "You are Primus.", noop_escalate, noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"meaning_row": 1}),
        )

        assert len(memory.intentions) == 1
        assert memory.intentions[0].meaning.name == "Test"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_falls_to_escalation_on_invalid_row():
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

        class EscalationMeaning(Meaning):
            name = "Escalation"
            def description(self): return "Escalation"
            def clarify(self): return None
            def reply(self): return "I'll figure this out"
            def path(self): return None
            def summarize(self): return None

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        async def noop_escalate(thread_text, meanings):
            return None

        meanings = [TestMeaning(p), EscalationMeaning(p)]
        memory = Memory(p, meanings)
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "unknown topic")

        async def run(url):
            p.thinking.url = url
            await conscious.understand(memory, p, meanings, lambda: "You are Primus.", noop_escalate, noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"meaning_row": 99}),
        )

        assert len(memory.intentions) == 1
        assert memory.intentions[0].meaning.name == "Escalation"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_escalation_with_no_code_uses_escalation_meaning():
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

        class EscalationMeaning(Meaning):
            name = "Escalation"
            def description(self): return "Escalation"
            def clarify(self): return None
            def reply(self): return "I'll figure this out"
            def path(self): return None
            def summarize(self): return None

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        async def noop_escalate(thread_text, meanings):
            return None

        meanings = [TestMeaning(p), EscalationMeaning(p)]
        memory = Memory(p, meanings)
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "unknown")

        async def run(url):
            p.thinking.url = url
            await conscious.understand(memory, p, meanings, lambda: "You are Primus.", noop_escalate, noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"meaning_row": 2}),
        )

        assert memory.intentions[0].meaning.name == "Escalation"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
