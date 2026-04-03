"""Outcome class for business operations - consistent result handling."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(kw_only=True)
class Outcome(Generic[T]):
    """Outcome of a business operation. Use for consistent result handling across business layer."""

    success: bool
    message: str
    data: T | None = None
