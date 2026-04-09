from application.platform.processes import on_separate_process_async


# ── Ego construction ─────────────────────────────────────────────────────────

async def test_ego_initializes_with_persona_and_memory():
    def isolated():
        import os
        import tempfile
        from application.core import agents
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        
        assert ego.persona is p
        assert ego.memory is not None
        assert ego.meanings[0].name == "Test"
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


# ── Pipeline ─────────────────────────────────────────────────────────────────

async def test_consciousness_returns_six_callables():
    def isolated():
        import os
        import tempfile
        from application.core import agents
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())

        consciousness = ego.consciousness()
        assert len(consciousness) == 6
        assert all(callable(step) for step in consciousness)
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


# ── Trigger ──────────────────────────────────────────────────────────────────

async def test_trigger_adds_signal_to_memory_and_nudges():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core import agents
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        
        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())

        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        ego.trigger(s)
        assert len(ego.memory.signals) == 1
        assert ego.worker.nudged == 1
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


async def test_trigger_ignores_signal_when_worker_stopped():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core import agents
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        ego.worker.stopped = True
        s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
        ego.trigger(s)
        assert len(ego.memory.signals) == 0
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


# ── Incept ───────────────────────────────────────────────────────────────────

async def test_incept_injects_perception_and_nudges():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core import agents
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona
        from application.core.brain.data import Perception

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        s = Signal(id="s1", event=SignalEvent.nudged, content="wake up", created_at=datetime(2026, 3, 15, 10, 0))
        p = Perception(impression="wake notification", thread=[s])
        ego.incept(p)
        assert len(ego.memory.perceptions) == 1
        assert ego.memory.perceptions[0].impression == "wake notification"
        assert ego.worker.nudged == 1
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


# ── Read ─────────────────────────────────────────────────────────────────────

async def test_read_returns_signals_sorted_by_time():
    def isolated():
        import os
        import tempfile
        from datetime import datetime
        from application.core import agents
        from application.core.brain.data import Signal, SignalEvent, Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        s1 = Signal(id="s1", event=SignalEvent.heard, content="second", created_at=datetime(2026, 3, 15, 10, 1))
        s2 = Signal(id="s2", event=SignalEvent.heard, content="first", created_at=datetime(2026, 3, 15, 10, 0))
        ego.memory.trigger(s1)
        ego.memory.trigger(s2)
        result = ego.read()
        assert result[0].id == "s2"
        assert result[1].id == "s1"
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


# ── Register and find ────────────────────────────────────────────────────────

async def test_register_stores_ego_and_find_retrieves_persona():
    def isolated():
        import os
        import tempfile
        from application.core import agents
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents.register(p, ego)
        found = agents.find(p.id)
        assert found.id == p.id
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


async def test_find_raises_when_not_registered():
    def isolated():
        import os
        import tempfile
        from application.core import agents

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        try:
            agents.find("nonexistent")
            assert False, "should have raised"
        except agents.MindError:
            pass
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


async def test_persona_returns_ego():
    def isolated():
        import os
        import tempfile

        from application.core import agents
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents.register(p, ego)
        assert agents.persona(p) is ego
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


# ── Unload ───────────────────────────────────────────────────────────────────

async def test_unload_persists_memory_and_unregisters():
    def isolated():
        import os
        import tempfile

        from application.core import agents, paths
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona
        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents.register(p, ego)
        ego.unload()

        try:
            agents.find(p.id)
            assert False, "should have raised"
        except agents.MindError:
            pass

        # Memory file should exist
        assert paths.mind_state(p.id).exists()
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


# ── Pairing codes ────────────────────────────────────────────────────────────

async def test_pair_generates_code_and_take_code_claims_it():
    def isolated():
        import os
        import tempfile

        from application.core import agents
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona
        from application.core.data import Channel

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents.register(p, ego)
        channel = Channel(type="telegram", name="12345")
        pair_code = agents.pair(p, channel)

        assert len(pair_code) == 6
        found_persona, ch_type, ch_name = agents.take_code(pair_code)
        assert found_persona.id == p.id
        assert ch_type == "telegram"
        assert ch_name == "12345"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


async def test_take_code_raises_on_invalid_code():
    def isolated():
        import os
        import tempfile

        from application.core import agents

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        try:
            agents.take_code("INVALID")
            assert False, "should have raised"
        except agents.AgentError:
            pass
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
        


# ── Identity ─────────────────────────────────────────────────────────────────

async def test_identity_includes_character():
    def isolated():
        import os
        import tempfile

        from application.core import agents, paths
        from application.core.brain.data import Meaning
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-ego", name="Primus", thinking=Model(name="llama3", url="not required"))
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0

            def run(self, *args):
                pass

            def nudge(self):
                self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "A test meaning"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())

        home = paths.home(p.id)
        home.mkdir(parents=True, exist_ok=True)
        (home / "person.md").write_text("")
        (home / "persona-trait.md").write_text("")
        (home / "wishes.md").write_text("")
        (home / "struggles.md").write_text("")
        (home / "traits.md").write_text("")

        result = ego.identity()
        assert "Primus" in result
        assert "# Who You Are" in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    
