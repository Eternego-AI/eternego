"""Brain meanings — recognized abilities of the persona.

Each meaning is a module that exposes a `Meaning` class. `Meaning(persona)` is
instantiated per-call; its `.intention()` returns a task-centered label (used
for matching), its `.prompt()` returns the text the persona reads while acting.
Any persona context a meaning needs — files, paths, name — is reached via
`self.persona`, never as a method argument.
"""

import importlib
import importlib.util
import pkgutil
import re
import types

from application.core import paths
from application.core.data import Model, Persona
from application.platform import logger

_discovered_modules = {}

for _, _name, _ in pkgutil.iter_modules(__path__):
    _discovered_modules[_name] = importlib.import_module(f".{_name}", __name__)


def available(persona):
    result = {}
    for name, module in _discovered_modules.items():
        if hasattr(module, "Meaning"):
            result[name] = module.Meaning(persona)
        else:
            logger.warning("Built-in meaning missing Meaning class", {"name": name})
    persona_dir = paths.meanings(persona.id)
    if persona_dir.exists():
        for f in sorted(persona_dir.glob("*.py")):
            instance = _load_file(persona, f)
            if instance is not None:
                result[f.stem] = instance
    return result


def load(persona, name):
    """Load one persona-specific meaning by name — used after save_meaning to
    bring a freshly-created meaning into memory without rescanning the dir."""
    f = paths.meanings(persona.id) / f"{name}.py"
    if not f.exists():
        return None
    return _load_file(persona, f)


def _load_file(persona, f):
    try:
        spec = importlib.util.spec_from_file_location(f.stem, f)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "Meaning"):
            return module.Meaning(persona)
        logger.warning("Meaning file missing Meaning class", {"file": str(f)})
    except Exception as e:
        logger.warning("Meaning file failed to load", {"file": str(f), "error": str(e)})
    return None


def save_meaning(persona_id, name, code):
    name = re.sub(r"[^\w-]", "", name.lower().replace(" ", "-"))[:60]
    if not name:
        raise ValueError("meaning name is empty after sanitization")

    code_object = compile(code, f"{name}.py", "exec")
    sandbox = types.ModuleType(f"_validate_{name}")
    try:
        exec(code_object, sandbox.__dict__)
        if not hasattr(sandbox, "Meaning"):
            raise ValueError("module has no Meaning class")
        test_persona = Persona(
            id=persona_id,
            name="validation",
            thinking=Model(name="", url=""),
        )
        instance = sandbox.Meaning(test_persona)
        intention_value = instance.intention()
        if not isinstance(intention_value, str):
            raise ValueError(f"Meaning.intention() returned {type(intention_value).__name__}, not str")
        prompt_value = instance.prompt()
        if not isinstance(prompt_value, str):
            raise ValueError(f"Meaning.prompt() returned {type(prompt_value).__name__}, not str")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"{type(e).__name__} during validation: {e}") from e

    directory = paths.meanings(persona_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.py").write_text(code)
    return name
