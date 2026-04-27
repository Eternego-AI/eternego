from application.platform.processes import on_separate_process_async


async def test_diagnose_reads_memory_and_health():
    """Diagnose reads memory.json (pretty-printed JSON array) and health.jsonl
    (one JSON object per line) and returns both alongside persona status."""
    def isolated():
        import asyncio
        import json
        import os
        import tempfile
        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        from application.business import persona as spec
        from application.core import paths
        from application.core.data import Model, Persona

        p = Persona(
            id="diagnose-test",
            name="Diag",
            thinking=Model(name="llama3", url="not required"),
            base_model="llama3",
            status="active",
        )
        paths.home(p.id).mkdir(parents=True, exist_ok=True)
        mem_path = paths.memory(p.id)
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_text(json.dumps([{"messages": [], "context": "carried"}], indent=2))

        health_path = paths.health_log(p.id)
        health_path.parent.mkdir(parents=True, exist_ok=True)
        health_path.write_text(
            json.dumps({"time": "2026-04-22T00:00:00+00:00", "loop_number": 1, "fault_count": 0, "fault_providers": []}) + "\n"
            + json.dumps({"time": "2026-04-22T00:01:00+00:00", "loop_number": 2, "fault_count": 0, "fault_providers": []}) + "\n"
        )

        outcome = asyncio.run(spec.diagnose(p))
        assert outcome.success, outcome.message
        assert outcome.data.status == "active"
        assert outcome.data.mind == {"messages": [], "context": "carried"}
        assert len(outcome.data.health) == 2
        assert outcome.data.health[0]["loop_number"] == 1
        assert outcome.data.health[1]["loop_number"] == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_diagnose_handles_missing_files():
    """When memory.json and health.jsonl don't exist, diagnose returns empty
    mind and health without error."""
    def isolated():
        import asyncio
        import os
        import tempfile
        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        from application.business import persona as spec
        from application.core import paths
        from application.core.data import Model, Persona

        p = Persona(
            id="diagnose-empty",
            name="Empty",
            thinking=Model(name="llama3", url="not required"),
            base_model="llama3",
            status="hibernate",
        )
        paths.home(p.id).mkdir(parents=True, exist_ok=True)

        outcome = asyncio.run(spec.diagnose(p))
        assert outcome.success, outcome.message
        assert outcome.data.status == "hibernate"
        assert outcome.data.mind == {}
        assert outcome.data.health == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
