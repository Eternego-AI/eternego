"""Skills — loadable knowledge documents for the persona.

Each skill module exposes a module-level `skill` instance of Skill with:
  name: str               — the key used for selection
  requires_permission: bool — (default False)
  description: str        — one-line summary shown during prepare
  instruction: str        — static usage hint (optional)
  execution()             — returns a callable: (persona) -> str

for_name(name)      — returns the Skill instance for a given name
all_skills()        — returns all Skill instances
descriptions()      — returns [(name, description)] for all skills
"""

import pkgutil
import importlib

_package = "application.core.brain.skills"


def _iter():
    for _, mod_name, _ in pkgutil.iter_modules(__path__):
        mod = importlib.import_module(f"{_package}.{mod_name}")
        s = getattr(mod, "skill", None)
        if s is not None:
            yield s


def for_name(name: str):
    """Return the Skill instance for the given name, or None if unknown."""
    for s in _iter():
        if s.name == name:
            return s
    return None


def all_skills():
    """Return all Skill instances."""
    return list(_iter())


def descriptions() -> list[tuple[str, str]]:
    """Return [(name, description)] for every skill."""
    return [(s.name, s.description) for s in _iter() if s.description]


# Convenience list for built-in skills (populated after module load)
def basics():
    """Return the list of built-in Skill instances."""
    from application.core.brain.skills import (
        being_persona, shell, python, notes, web_search, eternego,
    )
    return [
        being_persona.skill,
        shell.skill,
        python.skill,
        notes.skill,
        web_search.skill,
        eternego.skill,
    ]
