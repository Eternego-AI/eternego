"""Signals — classification and context helpers for perception threads.

classify(perceptions)   split into (active, inactive) based on last signal role.
context(inactive)       format inactive threads as a compact context block for prompts.
"""

from application.core.brain.data import Perception


def classify(perceptions: list[Perception]) -> tuple[list[Perception], list[Perception]]:
    """Split perceptions into (active, inactive).

    Active:   last signal is from user — thread still needs a response.
    Inactive: last signal is from assistant — thread has been addressed.
    """
    active, inactive = [], []
    for p in perceptions:
        if p.thread.signals and p.thread.signals[-1].prompt.role == "assistant":
            inactive.append(p)
        else:
            active.append(p)
    return active, inactive


