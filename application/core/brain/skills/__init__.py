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
import inspect
import pkgutil
import importlib

from application.core.brain.data import Skill
from application.core.data import Persona

_package = "application.core.brain.skills"


def built_in(persona: Persona):
    for _, mod_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{mod_name}")

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Skill) and obj is not Skill:
                yield obj(persona)

