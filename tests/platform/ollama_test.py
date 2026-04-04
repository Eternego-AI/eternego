from application.platform.processes import on_separate_process_async


async def test_get_sends_to_correct_path():
    def isolated():
        from application.platform import ollama
        ollama.assert_get(
            run=lambda: ollama.get("/api/tags"),
            validate=lambda r: None if r["path"] == "/api/tags" else (_ for _ in ()).throw(AssertionError(r["path"])),
            response={"models": []},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_returns_json_response():
    def isolated():
        from application.platform import ollama
        result = {}
        async def run():
            result["value"] = await ollama.get("/api/tags")
        ollama.assert_get(run=run, response={"models": [{"name": "llama3"}]})
        assert result["value"] == {"models": [{"name": "llama3"}]}
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_post_sends_correct_path_and_body():
    def isolated():
        from application.platform import ollama
        def validate(r):
            assert r["path"] == "/api/pull", r["path"]
            assert r["body"] == {"name": "llama3", "stream": False}, r["body"]
        ollama.assert_post(
            run=lambda: ollama.post("/api/pull", {"name": "llama3", "stream": False}),
            validate=validate,
            response={"status": "success"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_post_returns_json_response():
    def isolated():
        from application.platform import ollama
        result = {}
        async def run():
            result["value"] = await ollama.post("/api/chat", {"model": "llama3"})
        ollama.assert_post(run=run, response={"message": {"content": "Hello"}})
        assert result["value"] == {"message": {"content": "Hello"}}
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_delete_sends_correct_path_and_body():
    def isolated():
        from application.platform import ollama
        def validate(r):
            assert r["path"] == "/api/delete", r["path"]
            assert r["body"] == {"name": "llama3"}, r["body"]
        ollama.assert_delete(
            run=lambda: ollama.delete("/api/delete", {"name": "llama3"}),
            validate=validate,
            response={"status": "deleted"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
