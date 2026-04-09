from application.platform.processes import on_separate_process_async


async def test_does_nothing_when_no_thoughts():
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
        asyncio.run(conscious.decide(memory, p, lambda: "You are Primus.", noop_thinking))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_creates_recap_when_only_recap_returned():
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
        memory.realize(s, "task")
        thought = memory.understand(memory.perceptions[0], TestMeaning(p))
        memory.answer(thought, "acknowledged", SignalEvent.answered)

        async def run(url):
            p.thinking.url = url
            await conscious.decide(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"recap": "Already done"}),
        )

        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.recap
        assert last.content == "Already done"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_runs_action_and_informs_with_output():
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

        class ActionMeaning(Meaning):
            name = "Action"
            def description(self): return "Action meaning"
            def clarify(self): return None
            def reply(self): return None
            def path(self): return "Extract tool call"
            def summarize(self): return "Done"
            async def run(self, persona_response):
                async def action():
                    return "command output"
                return action

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        memory = Memory(p, [ActionMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "task")
        memory.understand(memory.perceptions[0], ActionMeaning(p))

        async def run(url):
            p.thinking.url = url
            await conscious.decide(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"tool": "shell.run", "command": "ls", "recap": "Running ls"}),
        )

        events = [s.event for s in memory.intentions[0].perception.thread]
        assert SignalEvent.decided in events
        assert SignalEvent.executed in events
        executed = [s for s in memory.intentions[0].perception.thread if s.event == SignalEvent.executed][0]
        assert "command output" in executed.content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_informs_error_when_run_raises():
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

        class BrokenMeaning(Meaning):
            name = "Broken"
            def description(self): return "Broken"
            def clarify(self): return None
            def reply(self): return None
            def path(self): return "Extract"
            def summarize(self): return None
            async def run(self, persona_response):
                raise RuntimeError("run exploded")

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        memory = Memory(p, [BrokenMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "task")
        memory.understand(memory.perceptions[0], BrokenMeaning(p))

        async def run(url):
            p.thinking.url = url
            await conscious.decide(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"tool": "x", "recap": "trying"}),
        )

        executed = [s for s in memory.intentions[0].perception.thread if s.event == SignalEvent.executed]
        assert len(executed) == 1
        assert "run exploded" in executed[0].content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recaps_when_action_returns_none():
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

        class NullActionMeaning(Meaning):
            name = "NullAction"
            def description(self): return "Null action"
            def clarify(self): return None
            def reply(self): return None
            def path(self): return "Extract"
            def summarize(self): return "Done"
            async def run(self, persona_response):
                return None

        def stream_json(obj):
            text = json.dumps(obj)
            return [{"message": {"content": c}} for c in text]

        memory = Memory(p, [NullActionMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        memory.trigger(s)
        memory.realize(s, "task")
        memory.understand(memory.perceptions[0], NullActionMeaning(p))

        async def run(url):
            p.thinking.url = url
            await conscious.decide(memory, p, lambda: "You are Primus.", noop_thinking)

        ollama.assert_call(
            run=run,
            response=stream_json({"tool": "x", "recap": "nothing to do"}),
        )

        last = memory.intentions[0].perception.thread[-1]
        assert last.event == SignalEvent.recap
        assert last.content == "nothing to do"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
