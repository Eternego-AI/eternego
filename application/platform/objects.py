"""Data base class and serialization utilities."""

import json as _json
from dataclasses import dataclass, field, fields
from pathlib import Path


@dataclass
class Data:
    """Base class for structured data objects."""
    pass


def safe(v) -> object:
    """Recursively serialize any value for logs and signals.

    Data objects: sensitive fields masked (None → "", value → "***").
    Use json() when full fidelity is needed (e.g. storage).
    """
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, Data):
        result = {}
        for f in fields(v):
            val = getattr(v, f.name)
            result[f.name] = ("" if val is None else "***") if f.metadata.get("sensitive") else safe(val)
        return result
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, dict):
        return {k: safe(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [safe(i) for i in v]
    try:
        _json.dumps(v)
        return v
    except (TypeError, ValueError):
        return repr(v)


def json(v) -> object:
    """Recursively serialize any value for storage (credentials included).

    Data objects: all fields included, no masking.
    Use safe() for logs and signals.
    """
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, Data):
        return {f.name: json(getattr(v, f.name)) for f in fields(v)}
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, dict):
        return {k: json(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [json(i) for i in v]
    try:
        _json.dumps(v)
        return v
    except (TypeError, ValueError):
        return repr(v)


def are_equal(a: Data, b: Data) -> bool:
    """True if two Data objects are equal by their full serialized form."""
    return json(a) == json(b)


def sensitive(default=None):
    """Field factory that marks a field as sensitive."""
    return field(default=default, metadata={"sensitive": True})
