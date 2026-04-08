from application.platform.processes import on_separate_process_async


async def test_recover_from_local_model_error():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning
        from application.core.exceptions import EngineConnectionError

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3"), base_model="llama3")
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
                self._error = None
            @property
            def idle(self): return True
            @property
            def error(self): return self._error
            def run(self, *args): pass
            def nudge(self): self.nudged += 1
            def reset(self): self._error = None

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        worker = FakeWorker()
        ego = agents.Ego(p, [TestMeaning(p)], worker)
        agents._personas[p.id] = ego

        error = EngineConnectionError("Model returned an invalid JSON response")
        result = asyncio.run(spec.recover(p, error))
        assert result.success, result.message

        assert worker._error is None
        assert worker.nudged >= 1

        messages = paths.read_jsonl(paths.conversation(p.id))
        assert any("distracted" in m["content"] for m in messages)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_recover_from_frontier_error():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.core.brain.data import Meaning
        from application.core.exceptions import FrontierError

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3"), base_model="llama3")
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
                self._error = None
            @property
            def idle(self): return True
            @property
            def error(self): return self._error
            def run(self, *args): pass
            def nudge(self): self.nudged += 1
            def reset(self): self._error = None

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        worker = FakeWorker()
        ego = agents.Ego(p, [TestMeaning(p)], worker)
        agents._personas[p.id] = ego

        error = FrontierError("Failed to contact frontier model")
        result = asyncio.run(spec.recover(p, error))
        assert result.success, result.message

        assert worker._error is None
        assert worker.nudged >= 1

        messages = paths.read_jsonl(paths.conversation(p.id))
        assert any("mentor" in m["content"] for m in messages)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
