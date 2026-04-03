"""Tools — discovers and calls @tool-decorated platform functions."""

import asyncio
import inspect

from application.platform.tool import Tool, registered_tools
from application.platform import logger


def discover() -> list[Tool]:
    """Return all registered tools from platform modules."""
    return registered_tools()


def document() -> str:
    """Return a description of available tools for model prompts.

    WARNING: This document is used in escalation prompts to teach models what
    tools are available. If you change how tools are dispatched (the JSON schema
    expected by Meaning.run()), update this document to match. The tool list is
    generated from the registry so it stays in sync automatically.
    """
    available = registered_tools()
    if not available:
        return "No tools are currently available."
    tool_list = "\n".join(
        f"- `{t.name}({', '.join(f'{k}: {v}' for k, v in t.params.items())}) -> {t.returns}`: {t.instruction}"
        for t in available
    )
    return (
        "Tools are platform functions the persona can use via the decide step.\n"
        "When path() returns JSON with {\"tool\": \"tool_name\", ...params},\n"
        "the default run() dispatches the call automatically.\n\n"
        f"{tool_list}"
    )


async def call(tool_name: str, **params) -> str:
    """Find a tool by name, call it, and return the result as a string.

    Never raises — on exception, returns the error message as the result.
    Handles tuple returns (code, output) from shell functions.
    """
    tools = {t.name: t for t in registered_tools()}
    tool = tools.get(tool_name)
    if not tool:
        return f"[error] Unknown tool: {tool_name}"

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
        logger.error("tools.call: exception", {"tool": tool_name, "error": str(e)})
        return f"[error] {e}"
