from application.platform.processes import on_separate_process_async

async def test_pair_generates_code():
    def isolated():
        import asyncio
        import os
        import tempfile

        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Channel, Model, Persona
        from application.core.brain.data import Meaning

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3"), base_model="llama3")
        p.channels = [Channel(type="telegram", name="")]
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
        result = asyncio.run(spec.pair(p, Channel(type="telegram", name="12345")))
        assert result.success, result.message
        assert len(result.data["pairing_code"]) == 6

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pair_fails_when_already_verified():
    def isolated():
        import asyncio
        import os
        import tempfile

        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Channel, Model, Persona
        from application.core.brain.data import Meaning

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        result = asyncio.run(spec.pair(
            Persona(id="test-persona", name="Primus", thinking=Model(name="llama3"), base_model="llama3"),
            Channel(type="telegram", name="x", verified_at="2026-03-15")
        ))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pair_fails_when_channel_not_on_persona():
    def isolated():
        import asyncio
        import os
        import tempfile

        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Channel, Model, Persona
        from application.core.brain.data import Meaning

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3"), base_model="llama3")
        p.channels = []
        result = asyncio.run(spec.pair(p, Channel(type="telegram", name="x")))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


