"""Signals — classification helpers for threads.

classify(threads)   split into (active, inactive) based on last occurrence cause role.
"""

from application.core.brain.data import Thread


def classify(threads: list[Thread]) -> tuple[list[Thread], list[Thread]]:
    """Split threads into (active, inactive).

    Active:   last occurrence was user-caused — thread still needs attention.
    Inactive: last occurrence was assistant-caused — thread has been addressed.
    """
    active, inactive = [], []
    for t in threads:
        if t.occurrences and t.occurrences[-1].cause.role == "user":
            active.append(t)
        else:
            inactive.append(t)
    return active, inactive
