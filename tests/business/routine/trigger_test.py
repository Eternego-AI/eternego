from application.platform.processes import on_separate_process_async

async def test_trigger_fires_matching_spec():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import routine
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning
        from application.platform import datetimes, filesystem

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-routine", name="Primus", thinking=Model(name="llama3", url="not required"))
        home = paths.home(p.id)
        home.mkdir(parents=True, exist_ok=True)
        for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
            (home / f).touch()
        
        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        class FakeWorker:
            def __init__(self):
                self.stopped = False
            def run(self, *args): pass
            def nudge(self): pass
        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents._personas[p.id] = ego

        current_time = datetimes.now().strftime("%H:%M")
        routines_path = paths.routines(p.id)
        routines_path.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(routines_path, {
            "routines": [
                {"spec": "oversee", "time": current_time},
                {"spec": "oversee", "time": "99:99"},
            ]
        })

        result = asyncio.run(routine.trigger(p))
        assert result.success, result.message
        assert "oversee" in result.message
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


async def test_trigger_fires_nothing_when_no_match():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import routine
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning
        from application.platform import filesystem

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-routine", name="Primus", thinking=Model(name="llama3", url="not required"))
        home = paths.home(p.id)
        home.mkdir(parents=True, exist_ok=True)
        for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
            (home / f).touch()
        
        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        class FakeWorker:
            def __init__(self):
                self.stopped = False
            def run(self, *args): pass
            def nudge(self): pass
        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents._personas[p.id] = ego

        routines_path = paths.routines(p.id)
        routines_path.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(routines_path, {
            "routines": [{"spec": "oversee", "time": "99:99"}]
        })

        result = asyncio.run(routine.trigger(p))
        assert result.success, result.message
        assert "none" in result.message
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


async def test_trigger_succeeds_when_no_routines_file():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import routine
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-routine", name="Primus", thinking=Model(name="llama3", url="not required"))
        home = paths.home(p.id)
        home.mkdir(parents=True, exist_ok=True)
        for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
            (home / f).touch()
        
        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        class FakeWorker:
            def __init__(self):
                self.stopped = False
            def run(self, *args): pass
            def nudge(self): pass
        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents._personas[p.id] = ego

        result = asyncio.run(routine.trigger(p))
        assert result.success, result.message
        assert "none" in result.message
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    


async def test_trigger_skips_unknown_spec():
    def isolated():
        import os
        import asyncio
        import tempfile
        from application.business import routine
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning
        from application.platform import datetimes, filesystem

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-routine", name="Primus", thinking=Model(name="llama3", url="not required"))
        home = paths.home(p.id)
        home.mkdir(parents=True, exist_ok=True)
        for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
            (home / f).touch()
        
        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        class FakeWorker:
            def __init__(self):
                self.stopped = False
            def run(self, *args): pass
            def nudge(self): pass
        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents._personas[p.id] = ego

        current_time = datetimes.now().strftime("%H:%M")
        routines_path = paths.routines(p.id)
        routines_path.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(routines_path, {
            "routines": [{"spec": "nonexistent_function", "time": current_time}]
        })

        result = asyncio.run(routine.trigger(p))
        assert result.success, result.message
        assert "none" in result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

