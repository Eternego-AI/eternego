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

    Used by learn() when teaching the frontier what tools exist. The tool
    list is generated from the @tool registry — adding a new platform tool with
    @tool makes it appear here automatically.
    """
    available = registered_tools()
    if not available:
        return "No tools are currently available."
    tool_list = "\n".join(
        f"- `{t.name}({', '.join(f'{k}: {v}' for k, v in t.params.items())}) -> {t.returns}`: {t.instruction}"
        for t in available
    )
    return (
        "Tools are platform functions the persona can call from a meaning's path.\n"
        "A meaning asks its model for JSON like {\"tools.<name>\": { ...args }}; decide\n"
        "dispatches that to the matching tool below.\n\n"
        f"{tool_list}"
    )


async def call(tool_name: str, **params) -> tuple[str, str]:
    """Find a tool by name, call it. Returns (status, result).

    status is one of: ok, failed, error.
    - ok: tool ran and returned a value (or exit 0 for tuple returns).
    - failed: tool ran but returned a non-zero exit (tuple return with code != 0).
    - error: tool raised or didn't exist.
    result is the stringified output.
    """
    logger.debug("tools.call", {"tool": tool_name, "params": params})
    tools = {t.name: t for t in registered_tools()}
    tool = tools.get(tool_name)
    if not tool:
        return ("error", f"unknown tool: {tool_name}")

    try:
        if inspect.iscoroutinefunction(tool.fn):
            result = await tool.fn(**params)
        else:
            result = await asyncio.to_thread(tool.fn, **params)

        if isinstance(result, tuple) and len(result) == 2:
            code, output = result
            return ("ok" if code == 0 else "failed", str(output))

        return ("ok", str(result))

    except Exception as e:
        logger.error("tools.call exception", {"tool": tool_name, "error": str(e)})
        return ("error", str(e))
