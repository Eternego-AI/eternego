from application.platform.processes import on_separate_process_async

async def test_hear_succeeds():
    def isolated():
        import asyncio
        import os
        import tempfile

        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Channel, Message, Model, Persona
        from application.core.brain.data import Meaning
        
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

        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None
        
        ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
        agents._personas[p.id] = ego
        result = asyncio.run(spec.hear(p, Message(channel=Channel(type="web", name="w1"), content="hello")))
        assert result.success, result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


