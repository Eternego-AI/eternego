"""Tools — the persona's capabilities exposed to the planner.

Each tool module exposes a module-level `tool` instance of Tool with:
  name: str               — the key used in plan steps
  requires_permission: bool — whether explicit permission is needed (default True)
  description: str        — one-line summary shown during focus
  instruction: str        — how-to shown in situation context when selected
  execution(**params)     — returns an async callable: async (persona) -> str

for_name(name)      — returns the Tool instance for a given name
all_tools()         — returns all non-internal Tool instances
descriptions()      — returns [(name, description)] for non-internal tools
"""

import pkgutil
import importlib

_package = "application.core.brain.tools"


def all_tools():
    for _, mod_name, _ in pkgutil.iter_modules(__path__):
        mod = importlib.import_module(f"{_package}.{mod_name}")
        t = getattr(mod, "tool", None)
        if t is not None:
            yield t


def for_name(name: str):
    """Return the Tool instance for the given name, or None if unknown."""
    for t in all_tools():
        if t.name == name:
            return t
    return None


def descriptions() -> list[tuple[str, str]]:
    """Return [(name, description)] for every non-internal tool."""
    return [(t.name, t.description) for t in all_tools() if t.description]

"""
TODO:
Except shell, an agent can not have any more tools. However, for a persona, as it can not change its home files through
shell, we need to define some tools to modify those. The ones that we have specific read and write, like person-identity
does not need any tool, but routine, destiny, history files need a tool.
Important:
Also consider meanings, setting a reminder and making a schedule are meaning that needs writing destiny tool.
"""