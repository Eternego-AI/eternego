from application.platform.processes import on_separate_process_async


async def test_healthy_tick_writes_health_log_and_nudges():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, filesystem, objects

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        class FakeWorker:
            def __init__(self):
                self.idle = True
                self.error = None
                self.stopped = False
                self._events = []
                self.loop_number = 0
                self.reset_called = False
                self.nudged = 0
                self.cleared = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.reset_called = True; self.error = None
            @property
            def events(self): return list(self._events)
            def clear_events(self): self._events = []; self.cleared += 1

        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        paths.destiny(p.id).mkdir(parents=True, exist_ok=True)
        ego = agents.Ego(p, FakeWorker())

        outcome = asyncio.run(spec.health_check(ego, datetimes.now()))
        assert outcome.success, outcome.message
        assert p.status == "active"
        # Healthy tick with no due entries = no reason to nudge a quiet worker
        assert ego.worker.nudged == 0
        assert ego.worker.cleared == 1

        entries = paths.read_jsonl(paths.health_log(p.id))
        assert len(entries) == 1, entries
        assert entries[0]["fault_count"] == 0
        assert entries[0]["fault_providers"] == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_frontier_fault_disables_frontier_and_persists_config():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, filesystem, objects
        from application.platform.asyncio_worker import Event

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        class FakeWorker:
            def __init__(self, events, loop_number):
                self.idle = True
                self.error = None
                self.stopped = False
                self._events = list(events)
                self.loop_number = loop_number
                self.nudged = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.error = None
            @property
            def events(self): return list(self._events)
            def clear_events(self): self._events = []

        p = Persona(
            id="test-persona",
            name="Primus",
            thinking=Model(name="llama3", url="not required"),
            base_model="llama3",
            frontier=Model(name="claude-opus-4-6", provider="anthropic", api_key="x", url="https://api.anthropic.com"),
            vision=Model(name="claude-haiku-4-5", provider="anthropic", api_key="x", url="https://api.anthropic.com"),
        )
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        paths.destiny(p.id).mkdir(parents=True, exist_ok=True)

        events = [Event(
            kind="fault", function="recognize", loop=1,
            provider="anthropic", url="https://api.anthropic.com",
            model_name="claude-opus-4-6", error="HTTP 429",
        )]
        ego = agents.Ego(p, FakeWorker(events, loop_number=1))

        outcome = asyncio.run(spec.health_check(ego, datetimes.now()))
        assert outcome.success, outcome.message
        assert p.frontier is None
        assert p.vision is None        # both used anthropic, both disabled
        assert p.status == "active"    # thinking is ollama, not sick
        # Disabling a capacity doesn't nudge — the tick reads the updated config inline
        assert ego.worker.nudged == 0

        reread = paths.read_json(paths.persona_identity(p.id))
        assert reread["frontier"] is None
        assert reread["vision"] is None

        entries = paths.read_jsonl(paths.health_log(p.id))
        assert entries[0]["fault_count"] == 1
        assert "anthropic" in entries[0]["fault_providers"]

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_vision_only_fault_disables_vision_leaves_frontier_alone():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, filesystem, objects
        from application.platform.asyncio_worker import Event

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        class FakeWorker:
            def __init__(self, events):
                self.idle = True
                self.error = None
                self.stopped = False
                self._events = list(events)
                self.loop_number = 1
                self.nudged = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.error = None
            @property
            def events(self): return list(self._events)
            def clear_events(self): self._events = []

        p = Persona(
            id="test-persona",
            name="Primus",
            thinking=Model(name="llama3", url="not required"),
            base_model="llama3",
            frontier=Model(name="gpt-4", provider="openai", api_key="x", url="https://api.openai.com"),
            vision=Model(name="claude-haiku-4-5", provider="anthropic", api_key="x", url="https://api.anthropic.com"),
        )
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        paths.destiny(p.id).mkdir(parents=True, exist_ok=True)

        events = [Event(kind="fault", function="realize", loop=1, provider="anthropic", url="...", model_name="claude-haiku-4-5", error="empty")]
        ego = agents.Ego(p, FakeWorker(events))

        outcome = asyncio.run(spec.health_check(ego, datetimes.now()))
        assert outcome.success
        assert p.vision is None
        assert p.frontier is not None   # openai didn't fault
        assert p.status == "active"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_thinking_fault_marks_sick_and_fires_shutdown_command():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, filesystem, objects, observer
        from application.platform.asyncio_worker import Event

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        class FakeWorker:
            def __init__(self, events):
                self.idle = True
                self.error = None
                self.stopped = False
                self._events = list(events)
                self.loop_number = 1
                self.nudged = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.error = None
            @property
            def events(self): return list(self._events)
            def clear_events(self): self._events = []

        # Thinking on anthropic — any anthropic fault means thinking is threatened
        p = Persona(
            id="test-persona",
            name="Primus",
            thinking=Model(name="claude-sonnet-4-6", provider="anthropic", api_key="x", url="https://api.anthropic.com"),
            base_model="",
            vision=Model(name="claude-haiku-4-5", provider="anthropic", api_key="x", url="https://api.anthropic.com"),
        )
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        paths.destiny(p.id).mkdir(parents=True, exist_ok=True)

        events = [Event(kind="fault", function="realize", loop=1, provider="anthropic", url="...", model_name="claude-haiku-4-5", error="HTTP 401")]
        ego = agents.Ego(p, FakeWorker(events))

        commands = []

        async def capture(command: observer.Command):
            commands.append((command.title, command.details))

        observer.subscribe(capture)

        result = {}

        async def run():
            result["outcome"] = await spec.health_check(ego, datetimes.now())
            await asyncio.sleep(0)  # let the dispatched task run

        asyncio.run(run())

        outcome = result["outcome"]
        assert outcome.success is True, outcome
        assert "sick" in outcome.message.lower()
        assert outcome.data is not None
        assert outcome.data.persona is p
        assert outcome.data.log_entry["fault_providers"] == ["anthropic"]

        assert p.status == "sick"
        assert ego.worker.nudged == 0   # no nudge when going down

        reread = paths.read_json(paths.persona_identity(p.id))
        assert reread["status"] == "sick"

        titles = [t for t, _ in commands]
        assert "Persona became sick" in titles

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_unexpected_worker_error_recovers_with_apology():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, filesystem, objects

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        class FakeWorker:
            def __init__(self):
                self.idle = True
                self.error = RuntimeError("unexpected bug")
                self.stopped = False
                self._events = []
                self.loop_number = 0
                self.reset_called = False
                self.nudged = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.reset_called = True; self.error = None
            @property
            def events(self): return list(self._events)
            def clear_events(self): self._events = []

        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        paths.destiny(p.id).mkdir(parents=True, exist_ok=True)
        ego = agents.Ego(p, FakeWorker())

        outcome = asyncio.run(spec.health_check(ego, datetimes.now()))
        assert outcome.success
        assert ego.worker.reset_called is True
        assert ego.worker.nudged >= 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_due_destiny_entries_are_processed_after_health():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona
        from application.platform import datetimes, filesystem, objects

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp

        class FakeWorker:
            def __init__(self):
                self.idle = True
                self.error = None
                self.stopped = False
                self._events = []
                self.loop_number = 0
                self.nudged = 0
            def run(self, *a): pass
            def nudge(self): self.nudged += 1
            def reset(self): self.error = None
            @property
            def events(self): return list(self._events)
            def clear_events(self): self._events = []

        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        paths.destiny(p.id).mkdir(parents=True, exist_ok=True)
        ego = agents.Ego(p, FakeWorker())

        past = datetimes.now().replace(microsecond=0)
        trigger = past.strftime("%Y-%m-%d %H:%M")
        paths.save_destiny_entry(p.id, "reminder", trigger, "drink water")

        outcome = asyncio.run(spec.health_check(ego, datetimes.now()))
        assert outcome.success

        remaining = list(paths.destiny(p.id).glob("*.md"))
        assert remaining == []
        history_files = list(paths.history(p.id).glob("*.md"))
        assert len(history_files) == 1

        assert any("drink water" in (m.content or "") for m in ego.memory.messages)

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
