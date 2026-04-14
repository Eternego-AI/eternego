from application.platform.processes import on_separate_process_async


async def test_get_sends_to_correct_path():
    def isolated():
        from application.platform import ollama

        async def run(url):
            await ollama.get(url, "/api/tags")

        def validate(r):
            assert r["path"] == "/api/tags", r["path"]

        ollama.assert_get(
            run=run,
            validate=validate,
            response={"models": []},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_returns_json_response():
    def isolated():
        from application.platform import ollama

        result = {}
        async def run(url):
            result["value"] = await ollama.get(url, "/api/tags")

        ollama.assert_get(run=run, response={"models": [{"name": "llama3"}]})
        assert result["value"] == {"models": [{"name": "llama3"}]}
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_post_sends_correct_path_and_body():
    def isolated():
        from application.platform import ollama

        async def run(url):
            await ollama.post(url, "/api/pull", {"name": "llama3", "stream": False})

        def validate(r):
            assert r["path"] == "/api/pull", r["path"]
            assert r["body"] == {"name": "llama3", "stream": False}, r["body"]

        ollama.assert_post(
            run=run,
            validate=validate,
            response={"status": "success"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_post_returns_json_response():
    def isolated():
        from application.platform import ollama

        result = {}
        async def run(url):
            result["value"] = await ollama.post(url, "/api/chat", {"model": "llama3"})

        ollama.assert_post(run=run, response={"message": {"content": "Hello"}})
        assert result["value"] == {"message": {"content": "Hello"}}
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_delete_sends_correct_path_and_body():
    def isolated():
        from application.platform import ollama

        async def run(url):
            await ollama.delete(url, "/api/delete", {"name": "llama3"})

        def validate(r):
            assert r["path"] == "/api/delete", r["path"]
            assert r["body"] == {"name": "llama3"}, r["body"]

        ollama.assert_delete(
            run=run,
            validate=validate,
            response={"status": "deleted"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_stream_yields_chunks():
    def isolated():
        import asyncio
        from application.platform import ollama

        chunks = []

        async def consume(url):
            async for chunk in ollama.stream(url, "/api/chat", {"model": "test"}):
                chunks.append(chunk)

        ollama.assert_call(
            run=lambda url: consume(url),
            responses=[
                [
                    {"message": {"content": "Hello"}, "done": False},
                    {"message": {"content": " world"}, "done": False},
                    {"message": {"content": ""}, "done": True},
                ]
            ],
        )
        assert len(chunks) == 3
        assert chunks[0]["message"]["content"] == "Hello"
        assert chunks[1]["message"]["content"] == " world"
        assert chunks[2]["done"] is True
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_stream_sends_correct_body():
    def isolated():
        import asyncio
        from application.platform import ollama

        async def consume(url):
            async for _ in ollama.stream(url, "/api/chat", {"model": "test", "format": "json", "messages": [{"role": "user", "content": "hi"}]}):
                pass

        def validate(r):
            assert r["body"]["model"] == "test"
            assert r["body"]["format"] == "json"
            assert r["body"]["messages"] == [{"role": "user", "content": "hi"}]

        ollama.assert_call(
            run=lambda url: consume(url),
            validate=validate,
            responses=[[{"message": {"content": "{}"}, "done": True}]],
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
