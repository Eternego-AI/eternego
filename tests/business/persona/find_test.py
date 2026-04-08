from application.platform.processes import on_separate_process_async

async def test_find_returns_persona():
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
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3"), base_model="llama3")
        from application.platform import objects, filesystem
        identity = paths.persona_identity(p.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(p))
        result = asyncio.run(spec.find(p.id))
        assert result.success, result.message
        assert result.data["persona"].name == "Primus"
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_find_fails_when_not_found():
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
        result = asyncio.run(spec.find("nonexistent"))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
