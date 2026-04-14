from application.platform.processes import on_separate_process_async

async def test_get_list_returns_empty_when_no_personas():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        outcome = asyncio.run(spec.get_list())
        assert outcome.success is False
        assert outcome.data.personas == []

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_list_returns_personas():
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
        p =Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        from application.platform import objects, filesystem
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        result = asyncio.run(spec.get_list())
        assert result.success, result.message
        assert len(result.data.personas) == 1

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

