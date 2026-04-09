from application.platform.processes import on_separate_process_async


async def test_call_returns_error_for_unknown_tool():
    def isolated():
        import asyncio
        from application.core.tools import call
        from application.platform.tool import _registry

        _registry.clear()
        result = asyncio.run(call("nonexistent.tool"))
        assert "[error]" in result
        assert "Unknown tool" in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_call_executes_sync_tool():
    def isolated():
        import asyncio
        from application.core.tools import call
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        name = _registry[0].name
        result = asyncio.run(call(name, a=2, b=3))
        assert result == "5"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_call_executes_async_tool():
    def isolated():
        import asyncio
        from application.core.tools import call
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Async greeting")
        async def greet(person: str) -> str:
            return f"Hello {person}"

        name = _registry[0].name
        result = asyncio.run(call(name, person="Primus"))
        assert result == "Hello Primus"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_call_handles_tuple_return_success():
    def isolated():
        import asyncio
        from application.core.tools import call
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Run command")
        def run(command: str) -> tuple:
            return 0, "output here"

        name = _registry[0].name
        result = asyncio.run(call(name, command="ls"))
        assert result == "output here"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_call_handles_tuple_return_failure():
    def isolated():
        import asyncio
        from application.core.tools import call
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Run command")
        def run(command: str) -> tuple:
            return 1, "permission denied"

        name = _registry[0].name
        result = asyncio.run(call(name, command="rm -rf"))
        assert "[exit code 1]" in result
        assert "permission denied" in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_call_handles_tool_with_name_parameter():
    def isolated():
        import asyncio
        from application.core.tools import call
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Rename a file")
        def rename(name: str, new_name: str) -> str:
            return f"renamed {name} to {new_name}"

        tool_name = _registry[0].name
        result = asyncio.run(call(tool_name, name="old.txt", new_name="new.txt"))
        assert result == "renamed old.txt to new.txt"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_call_catches_exceptions():
    def isolated():
        import asyncio
        from application.core.tools import call
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Exploding tool")
        def explode() -> str:
            raise RuntimeError("boom")

        name = _registry[0].name
        result = asyncio.run(call(name))
        assert "[error]" in result
        assert "boom" in result

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
