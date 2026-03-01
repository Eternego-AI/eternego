"""Rest — between-cycle resting state. Transitions to Rethink after idle delay."""

from application.core.brain.data import Thinking


class Rest(Thinking):
    """Rest mode: set after each cycle completes. Mind idles until the timer fires."""
