from application.platform.processes import on_separate_process_async

async def test_conversation_returns_messages():
    def isolated():
        import asyncio
        import os
        import json
        import tempfile
        from application.business import persona as spec
        from application.core import agents, paths
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        conv_path = paths.conversation(p.id)
        conv_path.parent.mkdir(parents=True, exist_ok=True)
        conv_path.write_text(
            json.dumps({"role": "person", "content": "hello"}) + "\n"
            + json.dumps({"role": "persona", "content": "hi"}) + "\n"
        )
        result = asyncio.run(spec.conversation(p))
        assert result.success, result.message
        assert len(result.data.messages) == 2

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_conversation_returns_empty_when_no_file():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import persona as spec
        from application.core import agents
        from application.core.data import Model, Persona

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        p = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="not required"), base_model="llama3")
        result = asyncio.run(spec.conversation(p))
        assert result.success, result.message
        assert result.data.messages == []
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
