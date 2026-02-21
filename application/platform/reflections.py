"""Reflections — runtime module inspection utilities."""

import inspect


def sorted_by(module, attribute: str) -> list[tuple[str, object]]:
    """Return all callables in a module that have the given attribute, sorted by {attribute}_order."""
    members = [
        (name, fn)
        for name, fn in inspect.getmembers(module)
        if callable(fn) and hasattr(fn, attribute)
    ]
    return sorted(members, key=lambda x: getattr(x[1], f"{attribute}_order", 99))


def has_ability(module, name: str, attribute: str) -> bool:
    """Return True if the module has a callable with the given name that has the given attribute."""
    fn = getattr(module, name, None)
    return fn is not None and callable(fn) and hasattr(fn, attribute)
