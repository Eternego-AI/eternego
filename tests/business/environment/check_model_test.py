from application.platform.processes import on_separate_process_async


async def test_check_model_succeeds():
    def isolated():
        import asyncio
        from application.business import environment
        from application.core import agents, gateways
        from application.platform import ollama
        from application.core.data import Model

        agents._personas.clear()
        gateways._active.clear()

        result = {}
        def run(url):
            result["value"] = asyncio.run(environment.check_model(Model(url=url, name="llama3")))

        ollama.assert_call(
            run=run,
            responses=[
                {"models": [{"name": "llama3"}]},
                {"response": "ok"},
            ],
        )
        assert result["value"].success is True

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_check_model_fails_when_not_found():
    def isolated():
        import asyncio
        from application.business import environment
        from application.core import agents, gateways
        from application.platform import ollama
        from application.core.data import Model

        agents._personas.clear()
        gateways._active.clear()

        result = {}
        def run(url):
            result["value"] = asyncio.run(environment.check_model(Model(url=url, name="nonexistent")))

        ollama.assert_call(
            run=run,
            response={"models": [{"name": "llama3"}]},
        )
        assert result["value"].success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
