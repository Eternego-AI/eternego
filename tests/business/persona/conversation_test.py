from application.platform.processes import on_separate_process_async

async def test_conversation_returns_messages():
    def isolated():
        import asyncio
        import os
        import json
        import tempfile
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        p = Persona(id="test-persona", name="Primus", model=Model(name="llama3"), base_model="llama3")
        conv_path = paths.conversation(p.id)
        conv_path.parent.mkdir(parents=True, exist_ok=True)
        conv_path.write_text(
            json.dumps({"role": "person", "content": "hello"}) + "\n"
            + json.dumps({"role": "persona", "content": "hi"}) + "\n"
        )
        result = asyncio.run(spec.conversation(p.id))
        assert result.success is True
        assert len(result.data["messages"]) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_conversation_returns_empty_when_no_file():
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
        result = asyncio.run(spec.conversation("no-conv"))
        assert result.success is True
        assert result.data["messages"] == []
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
