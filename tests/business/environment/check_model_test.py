from application.platform.processes import on_separate_process_async


async def test_check_model_succeeds():
    def isolated():
        import os
        import tempfile
        import subprocess
        from application.business import environment
        from application.core import agents, gateways
        from application.platform import ollama
        from application.core.data import Model

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        subprocess.run(["git", "config", "--global", "user.email", "test@test.com"], env={**os.environ, "HOME": tmp})
        subprocess.run(["git", "config", "--global", "user.name", "Test"], env={**os.environ, "HOME": tmp})
        result = {}
        async def run():
            result["value"] = await environment.check_model(Model(name="llama3"))
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
        import os
        import tempfile
        import subprocess
        from application.business import environment
        from application.core import agents, gateways
        from application.platform import ollama
        from application.core.data import Model

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        subprocess.run(["git", "config", "--global", "user.email", "test@test.com"], env={**os.environ, "HOME": tmp})
        subprocess.run(["git", "config", "--global", "user.name", "Test"], env={**os.environ, "HOME": tmp})
        result = {}
        async def run():
            result["value"] = await environment.check_model(Model(name="nonexistent"))
        ollama.assert_call(
            run=run,
            response={"models": [{"name": "llama3"}]},
        )
        assert result["value"].success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
