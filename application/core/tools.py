"""Tools — discovers and calls @tool-decorated platform functions."""

import asyncio
import inspect

from application.platform.tool import Tool, registered_tools
from application.platform import logger


def discover() -> list[Tool]:
    """Return all registered tools from platform modules."""
    return registered_tools()


async def call(name: str, **params) -> str:
    """Find a tool by name, call it, and return the result as a string.

    Never raises — on exception, returns the error message as the result.
    Handles tuple returns (code, output) from shell functions.
    """
    tools = {t.name: t for t in registered_tools()}
    tool = tools.get(name)
    if not tool:
        return f"[error] Unknown tool: {name}"

    try:
        if inspect.iscoroutinefunction(tool.fn):
            result = await tool.fn(**params)
        else:
            result = await asyncio.to_thread(tool.fn, **params)

        # Handle tuple returns (return_code, output) from shell functions
        if isinstance(result, tuple) and len(result) == 2:
            code, output = result
            if code != 0:
                return f"[exit code {code}] {output}"
            return str(output)

        return str(result)
    except Exception as e:
        logger.error("tools.call: exception", {"tool": name, "error": str(e)})
        return f"[error] {e}"
