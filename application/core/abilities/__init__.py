"""Brain abilities — the persona's one-shot mechanical vocabulary.

An ability is a named operation the persona can invoke. Each ability is one
file in this directory with a single top-level async function decorated with
`@ability("description")`. The function's own name is the ability's name.

Contract:
- Receives `persona` as the first positional argument (from the caller).
- Receives `**kwargs` for its named parameters (filled in by the model).
- Returns a string on success — a short, honest description of what happened —
  or a `Media` for abilities that produce visual output (e.g. take_screenshot,
  screen). The clock executor inlines the Media into the TOOL_RESULT message
  so the persona sees it on the next pass.
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

from application.core.data import Action


_TYPE_MAP = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "Path": "string",
}


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
        for param_name, param in inspect.signature(fn).parameters.items():
            if param_name == "persona":
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
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


def actions(persona) -> list[Action]:
    """Return an Action variant per ability this persona can use — used by
    cognitive functions to build a closed `one_of` schema enumerating every
    valid action the persona can emit. Each ability's params become typed
    fields on the Action; the Action's name is `tools.<ability_name>` to
    match the selector the persona writes in her decision items.

    Abilities with variadic params (`*args` / `**kwargs`) are skipped —
    their args are open-shaped and can't be typed for strict mode. The
    persona reaches the same capability via the underlying typed tools/
    abilities those variadic dispatchers forward to (e.g. `screen` →
    `desktop.<verb>` directly)."""
    out: list[Action] = []
    for a in available(persona):
        sig = inspect.signature(a.fn)
        if any(
            p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for p in sig.parameters.values()
        ):
            continue
        fields = [
            Action(
                name=p,
                type=_TYPE_MAP.get(type_str, "string"),
                description="",
                required=True,
            )
            for p, type_str in a.params.items()
        ]
        out.append(Action(name=f"tools.{a.name}", type="object", description=a.instruction, fields=fields))
    return out


async def call(persona, name: str, **args):
    """Dispatch an ability by name. Returns the ability's result — a string for
    most abilities, or a `Media` for abilities that produce visual output.
    Raises ValueError if the ability is unknown or unavailable for this
    persona; propagates any exception the ability raises."""
    for a in _registry:
        if a.name == name:
            if a.requires is not None and not a.requires(persona):
                raise ValueError(f"ability {name} not available for this persona")
            return await a.fn(persona, **args)
    raise ValueError(f"unknown ability: {name}")
