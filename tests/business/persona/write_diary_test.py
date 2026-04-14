from application.platform.processes import on_separate_process_async

async def test_write_diary_succeeds():
    def isolated():
        import asyncio
        import os
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
                name="DiaryBot", thinking=Model(name="llama3", url=url), channel=Channel(type="web", credentials={}),
            ))
            assert outcome.success, outcome.message
            persona_id = outcome.data.persona.id

            outcome = asyncio.run(spec.find(persona_id))
            persona = outcome.data.persona

            outcome = asyncio.run(spec.write_diary(persona))
            assert outcome.success, outcome.message

        ollama.assert_call(
            run=run,
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

