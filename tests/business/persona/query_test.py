from application.platform.processes import on_separate_process_async


async def test_query_returns_response():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona
        from application.platform import ollama

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
        result = {}
        async def run(url):
            p.thinking = Model(url=url, name="anything")
            result["value"] = await spec.query(p, {"role": "user", "content": "hi"})
        ollama.assert_call(
            run=run,
            response={"message": {"content": "Hello from the model"}},
        )
        assert result["value"].success is True
        assert result["value"].data.response == "Hello from the model"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

