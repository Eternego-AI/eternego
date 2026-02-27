"""Traits — the persona's capabilities exposed to the planner.

Each trait module exposes a module-level `trait` instance of Trait with:
  name: str               — the key used in plan steps
  requires_permission: bool — whether explicit permission is needed (default True)
  description: str        — one-line summary shown during prepare
  instruction: str        — how-to shown in situation context when selected
  execution(**params)     — returns an async callable: async (persona) -> str

for_name(name)      — returns the Trait instance for a given name
all_traits()        — returns all non-internal Trait instances
descriptions()      — returns [(name, description)] for non-internal traits
"""

import pkgutil
import importlib

_package = "application.core.brain.traits"


def _iter():
    for _, mod_name, _ in pkgutil.iter_modules(__path__):
        mod = importlib.import_module(f"{_package}.{mod_name}")
        t = getattr(mod, "trait", None)
        if t is not None:
            yield t


def for_name(name: str):
    """Return the Trait instance for the given name, or None if unknown."""
    for t in _iter():
        if t.name == name:
            return t
    return None


def all_traits():
    """Return all non-internal Trait instances."""
    return [t for t in _iter() if not getattr(t, "internal", False)]


def descriptions() -> list[tuple[str, str]]:
    """Return [(name, description)] for every non-internal trait."""
    return [(t.name, t.description) for t in all_traits() if t.description]
