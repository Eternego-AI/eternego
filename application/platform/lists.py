"""Lists — generic list utilities."""

from typing import Callable, TypeVar

T = TypeVar("T")


def filter_by(items: list[T], predicate: Callable[[T], bool]) -> list[T]:
    return [item for item in items if predicate(item)]
