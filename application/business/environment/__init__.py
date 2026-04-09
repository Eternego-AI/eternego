"""Environment — preparing and verifying the environment for a persona to grow."""

import importlib
import pkgutil

for _, _name, _ in pkgutil.iter_modules(__path__):
    _module = importlib.import_module(f".{_name}", __name__)
    globals()[_name] = getattr(_module, _name)
