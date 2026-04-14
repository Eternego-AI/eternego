from application.platform.processes import on_separate_process_async

async def test_loaded_returns_running_persona():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
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

        ego = agents.Ego(p, FakeWorker())
        agents._personas[p.id] = ego
        result = asyncio.run(spec.loaded(p))
        assert result.success, result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_loaded_fails_when_not_running():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="not-running", name="Ghost", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        result = asyncio.run(spec.loaded(p))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

