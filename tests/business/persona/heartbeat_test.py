from application.platform.processes import on_separate_process_async


async def test_heartbeat_calls_health_check():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import objects, filesystem

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        paths.destiny(p.id).mkdir(parents=True, exist_ok=True)

        class FakeWorker:
            def __init__(self):
                self.idle = True
                self.error = None
                self.stopped = False
                self.loop_number = 0
                self._events = []
            def run(self, *a): pass
            def nudge(self): pass
            def reset(self): pass
            @property
            def events(self): return list(self._events)
            def clear_events(self): self._events = []

        p.ego = agents.Ego(p, FakeWorker())

        outcome = asyncio.run(spec.heartbeat(p))
        assert outcome.success, outcome.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
