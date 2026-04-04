from application.platform.processes import on_separate_process_async


async def test_live_processes_due_destiny_entries():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning
    
        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"), base_model="llama3")
        from application.platform import objects, filesystem
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        home = paths.home(p.id)
        for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
            (home / f).touch()
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0
            def run(self, *args): pass
            def nudge(self): self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None
        
        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents._personas[p.id] = ego

        # Create a destiny entry that is due now
        from datetime import timedelta
        from application.platform import datetimes
        now = datetimes.now()
        past = now - timedelta(minutes=5)
        paths.save_destiny_entry(p.id, "reminder", past.strftime("%Y-%m-%d %H:%M"), "Call the dentist")

        result = asyncio.run(spec.live(p, now))
        assert result.success is True
        assert "1" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error



async def test_live_returns_nothing_due_when_empty():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"), base_model="llama3")
        from application.platform import objects, filesystem
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        home = paths.home(p.id)
        for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
            (home / f).touch()
        class FakeWorker:
            def __init__(self):
                self.stopped = False
                self.nudged = 0
            def run(self, *args): pass
            def nudge(self): self.nudged += 1

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None
        
        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents._personas[p.id] = ego

        from application.platform import datetimes
        result = asyncio.run(spec.live(p, datetimes.now()))
        assert result.success is True
        assert "Nothing due" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

