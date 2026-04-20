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

from application.core import paths
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
    import re
    name = re.sub(r"[^\w-]", "", name.lower().replace(" ", "-"))[:60]
    if not name:
        raise ValueError("meaning name is empty after sanitization")
    compile(code, f"{name}.py", "exec")
    directory = paths.meanings(persona_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.py").write_text(code)
    return name
