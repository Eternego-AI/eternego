"""Brain abilities — the persona's one-shot mechanical vocabulary.

An ability is a named operation the persona can invoke. Each ability is one
file in this directory with a single top-level async function decorated with
`@ability("description")`. The function's own name is the ability's name.

Contract:
- Receives `persona` as the first positional argument (from the caller).
- Receives `**kwargs` for its named parameters (filled in by the model).
- Returns a string on success — a short, honest description of what happened.
- Raises an exception on failure. The caller wraps it into a TOOL_RESULT with
  status=error.

Abilities touch only persona state (config, files via persona.id, outbound
signals). Anything that needs to read or write memory is a meaning, not an
ability — meanings carry memory through their `path` method. That line is
deliberate: tools < abilities < meanings by the state they see.

Discovery is automatic: adding a new `.py` with an `@ability`-decorated
function is enough.
"""

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Callable, get_type_hints


@dataclass
class Ability:
    name: str                                # the function's own name
    instruction: str                         # description shown to the model
    params: dict                             # {param_name: type_str} from the signature (persona excluded)
    returns: str                             # return type annotation as a string
    fn: Callable                             # the decorated async function
    requires: Callable | None = None         # optional predicate(persona) → bool; None means always available


_registry: list[Ability] = []


def ability(instruction: str, requires: Callable | None = None):
    """Decorator that registers a function as an ability.

    The ability's name is the function's own name. Params are captured from
    the function's signature, excluding `persona` which is implicit.

    `requires` is an optional predicate `(persona) -> bool` that decides
    whether the ability is available to a given persona. Used for abilities
    that depend on capability the persona may or may not have configured
    (e.g., `look_at` requires a vision model). Defaults to None — always
    available.
    """
    def decorator(fn):
        hints = get_type_hints(fn)
        params = {}
        for param_name in inspect.signature(fn).parameters:
            if param_name == "persona":
                continue
            type_hint = hints.get(param_name)
            params[param_name] = getattr(type_hint, "__name__", str(type_hint)) if type_hint else "str"
        return_hint = hints.get("return")
        returns = getattr(return_hint, "__name__", str(return_hint)) if return_hint else "str"
        _registry.append(Ability(
            name=fn.__name__,
            instruction=instruction,
            params=params,
            returns=returns,
            fn=fn,
            requires=requires,
        ))
        return fn
    return decorator


# Auto-discover ability modules so their decorators register.
for _, _name, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f".{_name}", __name__)


def available(persona) -> list[Ability]:
    """Return the abilities this persona can actually use.

    An ability is available unless its `requires` predicate exists and
    returns False for this persona."""
    return [a for a in _registry if a.requires is None or a.requires(persona)]


def names(persona) -> list[str]:
    """Return the sorted list of ability names available to this persona."""
    return sorted(a.name for a in available(persona))


def document(persona) -> str:
    """Format the persona's available abilities for inclusion in a prompt."""
    lines = []
    for a in sorted(available(persona), key=lambda x: x.name):
        params_str = ", ".join(f"{k}: {v}" for k, v in a.params.items())
        lines.append(f"- `{a.name}({params_str})` — {a.instruction}")
    return "\n".join(lines)


async def call(persona, name: str, **args) -> str:
    """Dispatch an ability by name. Returns the ability's string result.
    Raises ValueError if the ability is unknown or unavailable for this
    persona; propagates any exception the ability raises."""
    for a in _registry:
        if a.name == name:
            if a.requires is not None and not a.requires(persona):
                raise ValueError(f"ability {name} not available for this persona")
            return await a.fn(persona, **args)
    raise ValueError(f"unknown ability: {name}")
