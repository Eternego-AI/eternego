from application.platform.processes import on_separate_process_async


# ── Trigger and needs_realizing ──────────────────────────────────────────────

async def test_trigger_adds_signal():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        assert len(mind.signals) == 1
        assert mind.signals[0].id == "s1"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_needs_realizing_returns_unattached_heard_signals():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        mind.trigger(Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0)))
        mind.trigger(Signal(id="s2", event=SignalEvent.answered, content="hello", created_at=datetime(2026, 3, 15, 10, 0)))
        unattended = mind.needs_realizing
        assert len(unattended) == 1
        assert unattended[0].id == "s1"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Realize ──────────────────────────────────────────────────────────────────

async def test_realize_creates_perception():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        assert len(mind.perceptions) == 1
        assert mind.perceptions[0].impression == "greeting"
        assert s in mind.perceptions[0].thread

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_appends_to_existing_perception():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s1 = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        s2 = Signal(id="s2", event=SignalEvent.heard, content="how are you", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s1)
        mind.trigger(s2)
        mind.realize(s1, "greeting")
        mind.realize(s2, "greeting")
        assert len(mind.perceptions) == 1
        assert len(mind.perceptions[0].thread) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_clears_signal_from_needs_realizing():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        assert len(mind.needs_realizing) == 1
        mind.realize(s, "greeting")
        assert len(mind.needs_realizing) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_realize_removes_existing_thought_on_heard_signal():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s1 = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s1)
        mind.realize(s1, "greeting")
        mind.understand(mind.perceptions[0], TestMeaning(p))
        assert len(mind.intentions) == 1

        s2 = Signal(id="s2", event=SignalEvent.heard, content="actually never mind", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s2)
        mind.realize(s2, "greeting")
        assert len(mind.intentions) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Understand ───────────────────────────────────────────────────────────────

async def test_understand_creates_thought():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        assert len(mind.intentions) == 1
        assert thought.meaning.name == "Test"
        assert thought.id != ""

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_needs_understanding_returns_perceptions_without_thoughts():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s1 = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        s2 = Signal(id="s2", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s1)
        mind.trigger(s2)
        mind.realize(s1, "greeting")
        mind.realize(s2, "question")
        assert len(mind.needs_understanding) == 2

        mind.understand(mind.perceptions[0], TestMeaning(p))
        assert len(mind.needs_understanding) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Needs recognition / decision / conclusion ────────────────────────────────

async def test_needs_recognition_when_last_signal_is_heard():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        mind.understand(mind.perceptions[0], TestMeaning(p))
        assert len(mind.needs_recognition) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_needs_recognition_empty_when_no_reply():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class NoReplyMeaning(Meaning):
            name = "NoReply"
            def description(self): return "Meaning with no reply"
            def clarify(self): return None
            def reply(self): return None
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [NoReplyMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        mind.understand(mind.perceptions[0], NoReplyMeaning(p))
        assert len(mind.needs_recognition) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_needs_decision_when_answered_and_has_path():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        mind.answer(thought, "hi there", SignalEvent.answered)
        assert len(mind.needs_decision) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_needs_decision_when_no_reply_and_has_path():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class NoReplyMeaning(Meaning):
            name = "NoReply"
            def description(self): return "Meaning with no reply"
            def clarify(self): return None
            def reply(self): return None
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [NoReplyMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        mind.understand(mind.perceptions[0], NoReplyMeaning(p))
        assert len(mind.needs_decision) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_needs_conclusion_when_recap_present():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        mind.answer(thought, "done", SignalEvent.recap)
        assert len(mind.needs_conclusion) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Answer and inform ────────────────────────────────────────────────────────

async def test_answer_appends_signal_to_thread():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        mind.answer(thought, "hi there", SignalEvent.answered)
        assert len(thought.perception.thread) == 2
        assert thought.perception.thread[-1].content == "hi there"
        assert thought.perception.thread[-1].event == SignalEvent.answered

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_inform_appends_tool_result_to_thread():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        tool_signal = Signal(id="tool1", event=SignalEvent.executed, content="result: ok")
        mind.inform(thought, tool_signal)
        assert thought.perception.thread[-1].event == SignalEvent.executed
        assert "result: ok" in thought.perception.thread[-1].content

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Forget ───────────────────────────────────────────────────────────────────

async def test_forget_removes_thought_and_exclusive_signals():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        mind.answer(thought, "response", SignalEvent.answered)

        assert len(mind.intentions) == 1
        assert len(mind.signals) == 2

        mind.forget(thought)

        assert len(mind.intentions) == 0
        assert len(mind.perceptions) == 0
        assert len(mind.signals) == 0

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Most important ───────────────────────────────────────────────────────────

async def test_most_important_thought_selects_highest_priority():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s1 = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        s2 = Signal(id="s2", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 1))
        mind.trigger(s1)
        mind.trigger(s2)
        mind.realize(s1, "low")
        mind.realize(s2, "high")
        t1 = mind.understand(mind.perceptions[0], TestMeaning(p), priority=1)
        t2 = mind.understand(mind.perceptions[1], TestMeaning(p), priority=5)

        result = mind.most_important_thought([t1, t2])
        assert result is t2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_most_important_thought_returns_none_for_empty():
    def isolated():
        import os
        import tempfile
        from application.core.brain.data import Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        assert mind.most_important_thought([]) is None

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Settled ──────────────────────────────────────────────────────────────────

async def test_settled_when_nothing_to_process():
    def isolated():
        import os
        import tempfile
        from application.core.brain.data import Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        assert mind.settled is True

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_not_settled_when_signals_need_realizing():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        mind.trigger(Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0)))
        assert mind.settled is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Changed ──────────────────────────────────────────────────────────────────

async def test_changed_detects_new_signals():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        assert mind.changed() is False
        mind.trigger(Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0)))
        assert mind.changed() is True
        assert mind.changed() is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_changed_resets_after_signals_realized():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.changed()
        mind.realize(s, "greeting")
        assert mind.changed() is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Persist and remember roundtrip ───────────────────────────────────────────

async def test_persist_and_remember_roundtrip():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        meanings = [TestMeaning(p)]
        mind = Memory(p, meanings)

        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        mind.understand(mind.perceptions[0], meanings[0], priority=3)
        mind.answer(mind.intentions[0], "hi", SignalEvent.answered)

        mind.persist()

        mind2 = Memory(p, meanings)
        mind2.remember()

        assert len(mind2.signals) == 2
        assert len(mind2.perceptions) == 1
        assert mind2.perceptions[0].impression == "greeting"
        assert len(mind2.intentions) == 1
        assert mind2.intentions[0].meaning.name == "Test"
        assert mind2.intentions[0].priority == 3

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


# ── Prompts ──────────────────────────────────────────────────────────────────

async def test_prompts_builds_messages_from_thread():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s)
        mind.realize(s, "greeting")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        mind.answer(thought, "hi there", SignalEvent.answered)

        prompts = mind.prompts(thought)
        assert len(prompts) == 2
        assert prompts[0]["role"] == "user"
        assert prompts[1]["role"] == "assistant"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_prompts_collapses_before_last_summary():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.brain.mind.memory import Memory
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"))

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return "Please clarify"
            def reply(self): return "Reply prompt"
            def path(self): return "Extract JSON"
            def summarize(self): return "Summarize"

        mind = Memory(p, [TestMeaning(p)])
        s1 = Signal(id="s1", event=SignalEvent.heard, content="first question", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s1)
        mind.realize(s1, "topic")
        thought = mind.understand(mind.perceptions[0], TestMeaning(p))
        mind.answer(thought, "first answer", SignalEvent.answered)
        mind.answer(thought, "summary of above", SignalEvent.summarized)

        s2 = Signal(id="s2", event=SignalEvent.heard, content="second question", created_at=datetime(2026, 3, 15, 10, 0))
        mind.trigger(s2)
        mind.realize(s2, "topic")

        prompts = mind.prompts(thought)
        assert any("summary of above" in p["content"] for p in prompts)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
