from application.platform.processes import on_separate_process_async

async def test_pair_verifies_channel():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business.persona.pair import pair
        from application.core import paths
        from application.core.data import Persona, Model, Channel
        from application.platform import OS, objects, filesystem
        OS._secret_cache_only = True

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()

        persona = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="Not required"), base_model="llama3")
        persona.channels = [Channel(type="telegram", name="")]
        identity = paths.persona_identity(persona.id)
        identity.parent.mkdir(parents=True, exist_ok=True)
        filesystem.write_json(identity, objects.json(persona))

        channel = Channel(type="telegram", name="12345", credentials={"token": "t"})
        result = asyncio.run(pair(persona, channel))
        assert result.success, result.message
        assert result.data.persona.id == persona.id
        assert result.data.channel.name == "12345"
        assert result.data.channel.verified_at is not None

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pair_fails_on_unknown_channel_type():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business.persona.pair import pair
        from application.core.data import Persona, Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()

        persona = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="x"), base_model="llama3")
        persona.channels = [Channel(type="telegram", name="")]

        channel = Channel(type="discord", name="xyz", credentials={"token": "t"})
        result = asyncio.run(pair(persona, channel))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pair_fails_on_already_verified_channel():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business.persona.pair import pair
        from application.core.data import Persona, Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()

        persona = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="x"), base_model="llama3")
        persona.channels = [Channel(type="telegram", name="12345", verified_at="2020-01-01T00:00:00")]

        channel = Channel(type="telegram", name="12345", credentials={"token": "t"})
        result = asyncio.run(pair(persona, channel))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
