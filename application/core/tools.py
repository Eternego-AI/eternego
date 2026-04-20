"""Tools — discovers and calls @tool-decorated platform functions."""

import asyncio
import inspect

from application.core.data import Message, Prompt
from application.platform.tool import Tool, registered_tools
from application.platform import logger


def discover() -> list[Tool]:
    """Return all registered tools from platform modules."""
    return registered_tools()


def document() -> str:
    """Return a description of available tools for model prompts.

    Used by escalate() when teaching the frontier what tools exist. The tool
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
        "Tools are platform functions the persona can call from a meaning's prompt.\n"
        "A meaning asks its model for JSON like {\"tool\": \"<name>\", ...params}; the\n"
        "experience stage dispatches that to the matching tool below.\n\n"
        f"{tool_list}"
    )


async def call(tool_name: str, **params) -> Message:
    """Find a tool by name, call it, and return the result as a Message.

    String results become a text Message with a [tool] prompt.
    Dict results with 'source' become a Media Message.
    Tuple results (code, output) from shell functions are formatted as text.
    Exceptions become [tool_error] Messages.
    """
    logger.debug("tools.call", {"tool": tool_name, "params": params})
    tools = {t.name: t for t in registered_tools()}
    tool = tools.get(tool_name)
    if not tool:
        content = f"[error] Unknown tool: {tool_name}"
        return Message(content=content, prompt=Prompt(role="user", content=f"[{tool_name}] {content}"))

    try:
        if inspect.iscoroutinefunction(tool.fn):
            result = await tool.fn(**params)
        else:
            result = await asyncio.to_thread(tool.fn, **params)

        if isinstance(result, tuple) and len(result) == 2:
            code, output = result
            if code != 0:
                content = f"[exit code {code}] {output}"
            else:
                content = str(output)
            return Message(content=content, prompt=Prompt(role="user", content=f"[{tool_name}] {content}"))

        content = str(result)
        return Message(content=content, prompt=Prompt(role="user", content=f"[{tool_name}] {content}"))

    except Exception as e:
        logger.error("tools.call exception", {"tool": tool_name, "error": str(e)})
        content = f"[tool_error] {e}"
        return Message(content=content, prompt=Prompt(role="user", content=content))
