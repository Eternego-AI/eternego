from application.platform.processes import on_separate_process_async


async def test_create_succeeds():
    def isolated():
        import asyncio
        import os
        import tempfile
        from application.platform import ollama
        from application.business import persona as spec
        from application.core import agents, gateways
        from application.core.data import Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()

        def run(url):
            outcome = asyncio.run(spec.create(
                name="TestBot",
                thinking=Model(name="llama3", url=url),
                channel=Channel(type="web", credentials={}),
            ))
            assert outcome.success, outcome.message
            assert outcome.data["name"] == "TestBot"
            assert len(outcome.data["recovery_phrase"].split()) == 24

        ollama.assert_call(
            run=run,
            response={"message": {"content": "ok"}}
        )


    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_create_with_frontier_succeeds():
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
            result = asyncio.run(spec.create(
                name="FrontierBot",
                thinking=Model(name="llama3", url=url),
                channel=Channel(type="web", credentials={}),
                frontier=Model(name="claude-3-opus-20240229", provider="anthropic", credentials={"api_key": "test-key"}, url="https://api.anthropic.com"),
            ))
            assert result.success, result.message

        ollama.assert_call(
            run=run,
            response={"message": {"content": "ok"}}
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_create_with_remote_thinking_model():
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
            result = asyncio.run(spec.create(
                name="RemoteBot",
                thinking=Model(name="claude-3", provider="anthropic", credentials={"api_key": "test-key"}, url=url),
                channel=Channel(type="web", credentials={}),
            ))
            assert result.success, result.message
            assert result.data["name"] == "RemoteBot"

        ollama.assert_call(
            run=run,
            response={"message": {"content": "ok"}}
        )

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

