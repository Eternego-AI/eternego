from application.platform.processes import on_separate_process_async

async def test_hear_succeeds():
    def isolated():
        import asyncio
        import os
        import tempfile

        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Channel, Message, Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
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

        p.ego = agents.Ego(p, FakeWorker())
        from application.core.data import Channel
        result = asyncio.run(spec.hear(p, content="hello", channel=Channel(type="web", name="w1")))
        assert result.success, result.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


