"""Brain meanings — recognized abilities of the persona."""

import importlib
import importlib.util
import pkgutil

from application.core import paths

_discovered = {}

for _, _name, _ in pkgutil.iter_modules(__path__):
    _discovered[_name] = importlib.import_module(f".{_name}", __name__)


def available(persona=None):
    result = dict(_discovered)
    if persona:
        persona_dir = paths.meanings(persona.id)
        if persona_dir.exists():
            for f in sorted(persona_dir.glob("*.py")):
                try:
                    spec = importlib.util.spec_from_file_location(f.stem, f)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    result[f.stem] = module
                except Exception:
                    pass
    return result


def save_meaning(persona_id, name, code):
    import re
    name = re.sub(r"[^\w-]", "", name.lower().replace(" ", "-"))[:60]
    directory = paths.meanings(persona_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.py").write_text(code)
    return name
