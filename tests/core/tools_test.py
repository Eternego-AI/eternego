import asyncio

from application.core.tools import call
from application.platform.tool import tool, _registry


def _clear():
    _registry.clear()


def test_call_returns_error_for_unknown_tool():
    _clear()
    result = asyncio.run(call("nonexistent.tool"))
    assert "[error]" in result
    assert "Unknown tool" in result
    _clear()


def test_call_executes_sync_tool():
    _clear()

    @tool("Add two numbers")
    def add(a: int, b: int) -> int:
        return a + b

    result = asyncio.run(call("tools_test.add", a=2, b=3))
    assert result == "5"
    _clear()


def test_call_executes_async_tool():
    _clear()

    @tool("Async greeting")
    async def greet(person: str) -> str:
        return f"Hello {person}"

    result = asyncio.run(call("tools_test.greet", person="Primus"))
    assert result == "Hello Primus"
    _clear()


def test_call_handles_tuple_return_success():
    _clear()

    @tool("Run command")
    def run(command: str) -> tuple:
        return (0, "output here")

    result = asyncio.run(call("tools_test.run", command="ls"))
    assert result == "output here"
    _clear()


def test_call_handles_tuple_return_failure():
    _clear()

    @tool("Run command")
    def run(command: str) -> tuple:
        return (1, "permission denied")

    result = asyncio.run(call("tools_test.run", command="rm -rf"))
    assert "[exit code 1]" in result
    assert "permission denied" in result
    _clear()


def test_call_handles_tool_with_name_parameter():
    _clear()

    @tool("Rename a file")
    def rename(name: str, new_name: str) -> str:
        return f"renamed {name} to {new_name}"

    result = asyncio.run(call("tools_test.rename", name="old.txt", new_name="new.txt"))
    assert result == "renamed old.txt to new.txt"
    _clear()


def test_call_catches_exceptions():
    _clear()

    @tool("Exploding tool")
    def explode() -> str:
        raise RuntimeError("boom")

    result = asyncio.run(call("tools_test.explode"))
    assert "[error]" in result
    assert "boom" in result
    _clear()
