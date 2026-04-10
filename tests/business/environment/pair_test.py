from application.platform.processes import on_separate_process_async

async def test_pair_claims_code():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import environment
        from application.core import agents, gateways
        from application.core.data import Persona, Model, Channel
        from application.core.brain.data import Meaning
        from application.platform import OS
        OS._secret_cache_only = True

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()
        agents._personas.clear()
        gateways._active.clear()

        persona = Persona(id="test-persona", name="Primus", thinking=Model(name="llama3", url="Not required"), base_model="llama3")
        persona.channels = [Channel(type="telegram", name="")]

        class FakeWorker:
            def run(self, *args): pass
        class TestMeaning(Meaning):
            name = "Test"
            def description(self): return "Test"
            def clarify(self): return None
            def reply(self): return "Reply"
            def path(self): return None
            def summarize(self): return None

        ego = agents.Ego(persona, [TestMeaning(persona)], FakeWorker())
        agents._personas[persona.id] = ego

        pairing_code = agents.pair(persona, Channel(type="telegram", name="12345"))
        result = asyncio.run(environment.pair(pairing_code))
        assert result.success, result.message
        assert "persona_id" in result.data
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pair_fails_on_invalid_code():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.business import environment
        from application.core import agents, gateways
        from application.platform import OS
        OS._secret_cache_only = True

        os.environ["ETERNEGO_HOME"] = tempfile.mkdtemp()
        agents._personas.clear()
        gateways._active.clear()
        result = asyncio.run(environment.pair("INVALID"))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    
