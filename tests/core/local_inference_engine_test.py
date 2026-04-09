from application.platform.processes import on_separate_process_async


async def test_get_default_model_returns_first_model():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine

        result = {}
        async def run(url):
            result["value"] = await local_inference_engine.get_default_model(url)

        ollama.assert_call(run=run, response={"models": [{"name": "llama3:latest"}, {"name": "phi4:14b"}]})
        assert result["value"] == "llama3:latest", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_default_model_returns_none_when_no_models():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine

        result = {}
        async def run(url):
            result["value"] = await local_inference_engine.get_default_model(url)

        ollama.assert_call(run=run, response={"models": []})
        assert result["value"] is None, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pull_sends_correct_model_name():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine

        async def run(url):
            return await local_inference_engine.pull(url, "llama3:latest")

        def validate(r):
            assert r["path"] == "/api/pull", r["path"]
            assert r["body"]["name"] == "llama3:latest", r["body"]

        ollama.assert_call(
            run=run,
            validate=validate,
            response={"status": "success"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_register_sends_model_and_base():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine

        async def run(url):
            await local_inference_engine.register(url, "primus-llama3", "llama3:latest")
        
        def validate(r):
            assert r["path"] == "/api/create", r["path"]
            assert r["body"]["model"] == "primus-llama3", r["body"]
            assert r["body"]["from"] == "llama3:latest", r["body"]

        ollama.assert_call(
            run=run,
            validate=validate,
            response={},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_delete_sends_correct_model():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine

        result = {}
        async def run(url):
            result["value"] = await local_inference_engine.delete(url, "llama3:latest")

        def validate(r):
            assert r["path"] == "/api/delete", r["path"]
            assert r["body"]["name"] == "llama3:latest", r["body"]

        ollama.assert_call(run=run, validate=validate, response={})
        assert result["value"] is True, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_check_returns_true_when_model_exists():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine

        result = {}
        async def run(url):
            result["value"] = await local_inference_engine.check(url, "llama3:latest")

        ollama.assert_call(run=run, responses=[
            {"models": [{"name": "llama3:latest"}]},
            {"response": "ok"},
        ])
        assert result["value"] is True, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_check_returns_false_when_model_not_in_list():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine

        result = {}
        async def run(url):
            result["value"] = await local_inference_engine.check(url, "nonexistent:model")

        ollama.assert_call(run=run, response={"models": [{"name": "llama3:latest"}]})
        assert result["value"] is False, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
