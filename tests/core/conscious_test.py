from application.platform.processes import on_separate_process_async


# ── Realize ──────────────────────────────────────────────────────────────────

async def test_realize_does_nothing_when_no_signals():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        memory = Memory(p, [TestMeaning(p)])
        asyncio.run(conscious.realize(memory, p, lambda: "You are Primus."))
        assert len(memory.perceptions) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_routes_signal_to_new_impression():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.realize(memory, p, lambda: "You are Primus."),
            response=stream_json({"routes": [{"signal": 1, "threads": [], "new_impressions": ["greeting"]}]}),
        )

        assert len(memory.perceptions) == 1
        assert memory.perceptions[0].impression == "greeting"
        assert len(memory.needs_realizing) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_routes_signal_to_existing_thread():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.realize(memory, p, lambda: "You are Primus."),
            response=stream_json({"routes": [{"signal": 1, "threads": [1], "new_impressions": []}]}),
        )

        assert len(memory.perceptions) == 1
        assert len(memory.perceptions[0].thread) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_routes_signal_to_both_existing_and_new():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.realize(memory, p, lambda: "You are Primus."),
            response=stream_json({"routes": [{"signal": 1, "threads": [1], "new_impressions": ["topic B"]}]}),
        )

        assert len(memory.perceptions) == 2
        impressions = [p.impression for p in memory.perceptions]
        assert "topic A" in impressions
        assert "topic B" in impressions

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_skips_invalid_signal_number():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.realize(memory, p, lambda: "You are Primus."),
            response=stream_json({"routes": [{"signal": 999, "threads": [], "new_impressions": ["x"]}]}),
        )

        assert len(memory.needs_realizing) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Understand ───────────────────────────────────────────────────────────────

async def test_understand_does_nothing_when_no_perceptions():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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
        asyncio.run(conscious.understand(memory, p, [TestMeaning(p)], lambda: "You are Primus.", noop_escalate))
        assert len(memory.intentions) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_understand_picks_meaning_by_row():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.understand(memory, p, meanings, lambda: "You are Primus.", noop_escalate),
            response=stream_json({"meaning_row": 1}),
        )

        assert len(memory.intentions) == 1
        assert memory.intentions[0].meaning.name == "Test"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_understand_falls_to_escalation_on_invalid_row():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.understand(memory, p, meanings, lambda: "You are Primus.", noop_escalate),
            response=stream_json({"meaning_row": 99}),
        )

        assert len(memory.intentions) == 1
        assert memory.intentions[0].meaning.name == "Escalation"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_understand_escalation_with_no_code_uses_escalation_meaning():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.understand(memory, p, meanings, lambda: "You are Primus.", noop_escalate),
            response=stream_json({"meaning_row": 2}),
        )

        assert memory.intentions[0].meaning.name == "Escalation"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Recognize ────────────────────────────────────────────────────────────────

async def test_recognize_does_nothing_when_no_thoughts():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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
        asyncio.run(conscious.recognize(memory, p, lambda: "You are Primus.", noop_say))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_replies_on_heard_signal():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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
            run=lambda: conscious.recognize(memory, p, lambda: "You are Primus.", capture_say),
            response={"message": {"content": "Hello there!"}},
        )

        assert said == ["Hello there!"]
        last = memory.intentions[0].perception.thread[-1]
        assert last.event == SignalEvent.answered
        assert last.content == "Hello there!"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_uses_clarify_after_executed_signal():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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
            run=lambda: conscious.recognize(memory, p, lambda: "You are Primus.", noop_say),
            response={"message": {"content": "Let me try again"}},
        )

        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.clarified

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recognize_forgets_thought_when_no_path():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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
            run=lambda: conscious.recognize(memory, p, lambda: "You are Primus.", noop_say),
            response={"message": {"content": "Hi!"}},
        )

        assert len(memory.intentions) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Decide ───────────────────────────────────────────────────────────────────

async def test_decide_does_nothing_when_no_thoughts():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize the result"

        memory = Memory(p, [TestMeaning(p)])
        asyncio.run(conscious.decide(memory, p, lambda: "You are Primus."))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_creates_recap_when_only_recap_returned():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.decide(memory, p, lambda: "You are Primus."),
            response=stream_json({"recap": "Already done"}),
        )

        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.recap
        assert last.content == "Already done"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_runs_action_and_informs_with_output():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.decide(memory, p, lambda: "You are Primus."),
            response=stream_json({"tool": "shell.run", "command": "ls", "recap": "Running ls"}),
        )

        events = [s.event for s in memory.intentions[0].perception.thread]
        assert SignalEvent.decided in events
        assert SignalEvent.executed in events
        executed = [s for s in memory.intentions[0].perception.thread if s.event == SignalEvent.executed][0]
        assert "command output" in executed.content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_informs_error_when_run_raises():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.decide(memory, p, lambda: "You are Primus."),
            response=stream_json({"tool": "x", "recap": "trying"}),
        )

        executed = [s for s in memory.intentions[0].perception.thread if s.event == SignalEvent.executed]
        assert len(executed) == 1
        assert "run exploded" in executed[0].content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_decide_recaps_when_action_returns_none():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        ollama.assert_call(
            run=lambda: conscious.decide(memory, p, lambda: "You are Primus."),
            response=stream_json({"tool": "x", "recap": "nothing to do"}),
        )

        last = memory.intentions[0].perception.thread[-1]
        assert last.event == SignalEvent.recap
        assert last.content == "nothing to do"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Conclude ─────────────────────────────────────────────────────────────────

async def test_conclude_does_nothing_when_no_thoughts():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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
        asyncio.run(conscious.conclude(memory, p, lambda: "You are Primus.", noop_say))

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_conclude_summarizes_with_model():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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
            run=lambda: conscious.conclude(memory, p, lambda: "You are Primus.", capture_say),
            response={"message": {"content": "Task completed successfully."}},
        )

        assert said == ["Task completed successfully."]
        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.summarized

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_conclude_uses_recap_when_no_summarize():
    def isolated():
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
        p = Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))

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

        asyncio.run(conscious.conclude(memory, p, lambda: "You are Primus.", noop_say))

        last = thought.perception.thread[-1]
        assert last.event == SignalEvent.summarized
        assert last.content == "all done here"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
