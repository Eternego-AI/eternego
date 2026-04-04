from application.platform.processes import on_separate_process_async


async def test_tool_decorator_registers_tool():
    def isolated():
        from application.platform.tool import tool, _registry, Tool

        _registry.clear()

        @tool("Run a shell command")
        def execute(command: str) -> str:
            pass

        assert len(_registry) == 1
        t = _registry[0]
        assert isinstance(t, Tool)
        assert t.instruction == "Run a shell command"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_extracts_params_from_signature():
    def isolated():
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Search files")
        def search(pattern: str, directory: str) -> list:
            pass

        t = _registry[0]
        assert "pattern" in t.params
        assert "directory" in t.params
        assert t.params["pattern"] == "str"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_extracts_return_type():
    def isolated():
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Get count")
        def count() -> int:
            pass

        t = _registry[0]
        assert t.returns == "int"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_derives_name_from_module_and_function():
    def isolated():
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Test")
        def my_function() -> str:
            pass

        t = _registry[0]
        assert t.name.endswith(".my_function")

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_tool_returns_original_function():
    def isolated():
        from application.platform.tool import tool, _registry

        _registry.clear()

        @tool("Test")
        def original():
            return 42

        assert original() == 42

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
