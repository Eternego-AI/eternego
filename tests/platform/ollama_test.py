from application.platform import ollama


def test_get_sends_to_correct_path():
    ollama.assert_get(
        run=lambda: _run(ollama.get("/api/tags")),
        validate=lambda r: _assert_equal(r["path"], "/api/tags"),
        response={"models": []},
    )


def test_get_returns_json_response():
    result = {}
    ollama.assert_get(
        run=lambda: _capture(result, ollama.get("/api/tags")),
        response={"models": [{"name": "llama3"}]},
    )
    assert result["value"] == {"models": [{"name": "llama3"}]}


def test_post_sends_correct_path_and_body():
    ollama.assert_post(
        run=lambda: _run(ollama.post("/api/pull", {"name": "llama3", "stream": False})),
        validate=lambda r: (
            _assert_equal(r["path"], "/api/pull"),
            _assert_equal(r["body"], {"name": "llama3", "stream": False}),
        ),
        response={"status": "success"},
    )


def test_post_returns_json_response():
    result = {}
    ollama.assert_post(
        run=lambda: _capture(result, ollama.post("/api/chat", {"model": "llama3"})),
        response={"message": {"content": "Hello"}},
    )
    assert result["value"] == {"message": {"content": "Hello"}}


def test_delete_sends_correct_path_and_body():
    ollama.assert_delete(
        run=lambda: _run(ollama.delete("/api/delete", {"name": "llama3"})),
        validate=lambda r: (
            _assert_equal(r["path"], "/api/delete"),
            _assert_equal(r["body"], {"name": "llama3"}),
        ),
        response={"status": "deleted"},
    )


async def _run(coro):
    await coro


async def _capture(result, coro):
    result["value"] = await coro


def _assert_equal(actual, expected):
    assert actual == expected, f"Expected {expected}, got {actual}"
