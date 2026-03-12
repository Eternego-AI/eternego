"""Tool — decorator and dataclass for exposing platform functions to the persona."""

import inspect
from dataclasses import dataclass
from typing import Callable, get_type_hints


@dataclass
class Tool:
    name: str             # module.function, e.g. "shell.run"
    instruction: str      # what this tool does, when to use it
    params: dict           # {param_name: type_str} from signature
    returns: str          # return type annotation as string
    fn: Callable          # the decorated function reference


# Registry of all decorated tools
_registry: list[Tool] = []


def tool(instruction: str):
    """Decorator that marks a platform function as an exposable tool.

    Derives name from module.function, params from signature, returns from annotation.
    The instruction string tells the model what the tool does and when to use it.
    """
    def decorator(fn):
        module = fn.__module__.rsplit(".", 1)[-1]  # e.g. "linux" from "application.platform.linux"
        name = f"{module}.{fn.__name__}"

        hints = get_type_hints(fn)
        params = {}
        for param_name, param in inspect.signature(fn).parameters.items():
            type_hint = hints.get(param_name)
            params[param_name] = getattr(type_hint, "__name__", str(type_hint)) if type_hint else "str"

        return_hint = hints.get("return")
        returns = getattr(return_hint, "__name__", str(return_hint)) if return_hint else "str"

        _registry.append(Tool(
            name=name,
            instruction=instruction,
            params=params,
            returns=returns,
            fn=fn,
        ))

        return fn
    return decorator


def registered_tools() -> list[Tool]:
    """Return all registered tools."""
    return list(_registry)
