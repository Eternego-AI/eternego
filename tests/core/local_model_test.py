from application.platform.processes import on_separate_process_async


async def test_chat_returns_message_content():
    def isolated():
        import asyncio, json
        from application.platform import ollama
        from application.core import local_model
        result = {}
        async def run():
            result["value"] = await local_model.chat("llama3", [{"role": "user", "content": "hi"}])
        ollama.assert_call(run=run, response={"message": {"content": "Hello!"}})
        assert result["value"] == "Hello!", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_sends_correct_payload():
    def isolated():
        import asyncio
        from application.platform import ollama
        from application.core import local_model
        def validate(r):
            assert r["path"] == "/api/chat", r["path"]
            assert r["body"]["model"] == "llama3", r["body"]
        ollama.assert_call(
            run=lambda: local_model.chat("llama3", [{"role": "user", "content": "hi"}]),
            validate=validate,
            response={"message": {"content": "Hello!"}},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_parses_json_from_response():
    def isolated():
        from application.platform import ollama
        from application.core import local_model
        result = {}
        async def run():
            result["value"] = await local_model.chat_json("llama3", [])
        ollama.assert_call(run=run, response={"message": {"content": '{"answer": 42}'}})
        assert result["value"] == {"answer": 42}, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_generate_returns_stripped_response():
    def isolated():
        from application.platform import ollama
        from application.core import local_model
        result = {}
        async def run():
            result["value"] = await local_model.generate("llama3", "prompt")
        ollama.assert_call(run=run, response={"response": "  generated text  "})
        assert result["value"] == "generated text", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_generate_sends_to_correct_path():
    def isolated():
        from application.platform import ollama
        from application.core import local_model
        def validate(r):
            assert r["path"] == "/api/generate", r["path"]
            assert r["body"]["model"] == "llama3", r["body"]
        ollama.assert_call(
            run=lambda: local_model.generate("llama3", "hello"),
            validate=validate,
            response={"response": "ok"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
