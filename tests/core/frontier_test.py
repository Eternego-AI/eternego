from application.platform.processes import on_separate_process_async


async def test_chat_calls_anthropic_with_correct_model():
    def isolated():
        import asyncio
        from application.core import frontier
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", credentials={"api_key": "test"})
        result = {}

        def assert_equal(actual, expected):
            assert actual == expected, f"Expected {expected}, got {actual}"

        anthropic.assert_chat(
            run=lambda: result.update(text=asyncio.run(frontier.chat(model, "hello"))),
            validate=lambda r: assert_equal(r["body"]["model"], "claude-3"),
            response={"content": [{"text": "Claude says hi"}]},
        )
        assert result["text"] == "Claude says hi"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_calls_openai_with_correct_model():
    def isolated():
        import asyncio
        from application.core import frontier
        from application.core.data import Model
        from application.platform import openai

        model = Model(name="gpt-4", provider="openai", credentials={"api_key": "test"})
        result = {}

        def assert_equal(actual, expected):
            assert actual == expected, f"Expected {expected}, got {actual}"

        openai.assert_chat(
            run=lambda: result.update(text=asyncio.run(frontier.chat(model, "hello"))),
            validate=lambda r: assert_equal(r["body"]["model"], "gpt-4"),
            response={"choices": [{"message": {"content": "GPT says hi"}}]},
        )
        assert result["text"] == "GPT says hi"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_chat_json_calls_anthropic():
    def isolated():
        import asyncio
        from application.core import frontier
        from application.core.data import Model
        from application.platform import anthropic

        model = Model(name="claude-3", provider="anthropic", credentials={"api_key": "test"})
        result = {}
        anthropic.assert_chat_json(
            run=lambda: result.update(data=asyncio.run(frontier.chat_json(model, "give json"))),
            response={"content": [{"text": '{"answer": 42}'}]},
        )
        assert result["data"] == {"answer": 42}

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_read_parses_anthropic_export():
    def isolated():
        import json
        import asyncio
        from application.core import frontier

        export = json.dumps([
            {"chat_messages": [{"sender": "human", "text": "Hi"}, {"sender": "assistant", "text": "Hello"}]}
        ])
        result = asyncio.run(frontier.read(export, "claude"))
        assert len(result) == 2
        assert result[0]["role"] == "user"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_read_parses_openai_export():
    def isolated():
        import json
        import asyncio
        from application.core import frontier

        export = json.dumps([
            {"mapping": {"n1": {"message": {"author": {"role": "user"}, "content": {"parts": ["Hi"]}}}}}
        ])
        result = asyncio.run(frontier.read(export, "openai"))
        assert len(result) == 1
        assert result[0]["content"] == "Hi"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_read_raises_on_invalid_data():
    def isolated():
        import asyncio
        from application.core import frontier
        from application.core.exceptions import FrontierError

        try:
            asyncio.run(frontier.read("not json", "claude"))
            assert False, "should have raised"
        except FrontierError:
            pass

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
