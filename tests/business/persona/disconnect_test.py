from application.platform.processes import on_separate_process_async

async def test_disconnect_succeeds():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways
        from application.core.data import Channel, Model, Persona
        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"), base_model="llama3")
        ch = Channel(type="web", name="w1")
        gateways.of(p).add(ch, {"type": "web"})
        result = asyncio.run(spec.disconnect(p, ch))
        assert result.success is True

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
