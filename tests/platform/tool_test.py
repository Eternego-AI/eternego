from application.platform.tool import tool, _registry, Tool


def _clear_registry():
    _registry.clear()


def test_tool_decorator_registers_tool():
    _clear_registry()

    @tool("Run a shell command")
    def execute(command: str) -> str:
        pass

    assert len(_registry) == 1
    t = _registry[0]
    assert isinstance(t, Tool)
    assert t.instruction == "Run a shell command"
    _clear_registry()


def test_tool_extracts_params_from_signature():
    _clear_registry()

    @tool("Search files")
    def search(pattern: str, directory: str) -> list:
        pass

    t = _registry[0]
    assert "pattern" in t.params
    assert "directory" in t.params
    assert t.params["pattern"] == "str"
    _clear_registry()


def test_tool_extracts_return_type():
    _clear_registry()

    @tool("Get count")
    def count() -> int:
        pass

    t = _registry[0]
    assert t.returns == "int"
    _clear_registry()


def test_tool_derives_name_from_module_and_function():
    _clear_registry()

    @tool("Test")
    def my_function() -> str:
        pass

    t = _registry[0]
    # module name is the last part of __module__
    assert t.name.endswith(".my_function")
    _clear_registry()


def test_tool_returns_original_function():
    _clear_registry()

    @tool("Test")
    def original():
        return 42

    assert original() == 42
    _clear_registry()
