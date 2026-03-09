"""Meanings — built-in meaning modules for the brain.

Each module exposes a module-level `meaning` instance of Meaning with:
  name, definition, purpose, tools, skills, path

Persona-specific meanings live as JSON files in persona/meanings/.

all_meanings()     — all built-in Meaning instances
for_name(name)     — return a built-in Meaning by name, or None
"""

import pkgutil
import importlib

from application.core.brain.data import Meaning

_package = "application.core.brain.meanings"


def all_meanings() -> list[Meaning]:
    """Return all built-in Meaning instances."""
    result = []
    for _, mod_name, _ in pkgutil.iter_modules(__path__):
        mod = importlib.import_module(f"{_package}.{mod_name}")
        m = getattr(mod, "meaning", None)
        if m is not None and isinstance(m, Meaning):
            result.append(m)
    return result


def for_name(name: str) -> Meaning | None:
    """Return a built-in Meaning by name, or None."""
    for m in all_meanings():
        if m.name == name:
            return m
    return None
