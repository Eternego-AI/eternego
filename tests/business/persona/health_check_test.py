from application.platform.processes import on_separate_process_async


async def test_health_check_succeeds_with_no_error_and_no_due():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, objects, filesystem

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
                self.reset_called = False
                self.nudged = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.reset_called = True

        p.ego = agents.Ego(p, FakeWorker())

        outcome = asyncio.run(spec.health_check(p, datetimes.now()))
        assert outcome.success, outcome.message
        assert p.ego.worker.reset_called is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_health_check_recovers_when_worker_errored():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, channels, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, objects, filesystem

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
                self.error = RuntimeError("boom")
                self.reset_called = False
                self.nudged = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.reset_called = True

        p.ego = agents.Ego(p, FakeWorker())

        outcome = asyncio.run(spec.health_check(p, datetimes.now()))
        assert outcome.success, outcome.message
        assert p.ego.worker.reset_called is True
        assert p.ego.worker.nudged >= 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
