"""Lists — generic list utilities."""

from typing import Callable, TypeVar

T = TypeVar("T")


def filter_by(items: list[T], predicate: Callable[[T], bool]) -> list[T]:
    return [item for item in items if predicate(item)]


def as_list(value) -> list:
    """Normalize a value to a list — wraps a string, returns a list as-is, empty otherwise."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []
