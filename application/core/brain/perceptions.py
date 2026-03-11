"""Perceptions — formatting helpers for Perception nodes."""

from application.core.brain.data import Perception
from application.core.brain import signals


def thread(perception: Perception) -> str:
    """Return a string representation of a perception and its thread."""
    lines = [f"# {perception.impression}"]
    lines += [signals.as_text(s) for s in perception.thread]
    return "\n".join(lines)
