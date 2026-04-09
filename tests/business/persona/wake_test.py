from application.platform.processes import on_separate_process_async

async def test_wake_succeeds():
    def isolated():
        import os
        import asyncio
        import tempfile

        from application.business import persona as spec
        from application.core import agents, gateways
        from application.platform import ollama
        from application.core.data import Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True
        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()

        def run(url):
            outcome = asyncio.run(spec.create(
                name="WakeBot", thinking=Model(name="llama3", url=url), channel=Channel(type="web", credentials={}),
            ))
            assert outcome.success, outcome.message
            persona_id = outcome.data["persona_id"]

            # Nap first to unload
            outcome = asyncio.run(spec.find(persona_id))
            asyncio.run(spec.nap(outcome.data["persona"]))

            # Wake
            from application.platform.asyncio_worker import Worker
            outcome = asyncio.run(spec.wake(persona_id, Worker()))
            assert outcome.success, outcome.message

        ollama.assert_call(
            run=run,
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

