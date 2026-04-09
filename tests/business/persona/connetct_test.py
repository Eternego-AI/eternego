from application.platform.processes import on_separate_process_async

async def test_connect_web_channel_succeeds():
    def isolated():
        import tempfile
        import os
        import asyncio
        from application.core import agents, gateways
        from application.core.data import Model, Channel
        from application.business import persona as spec
        from application.platform import ollama
        from application.platform import OS
        OS._secret_cache_only = True

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()

        def run(url):
            outcome = asyncio.run(spec.create(name="ConnectBot", thinking=Model(name="llama3", url=url), channel=Channel(type="web", credentials={})))
            assert outcome.success, outcome.message
            persona_id = outcome.data["persona_id"]
            outcome = asyncio.run(spec.find(persona_id))
            persona = outcome.data["persona"]
            ch = Channel(type="web", name="new-web")
            outcome = asyncio.run(spec.connect(persona, ch))
            assert outcome.success, outcome.message

        ollama.assert_call(
            run=run,
            responses=[
                {"models": [{"name": "eternego-test"}]},
                {"response": "ok"},
            ],
        )
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

