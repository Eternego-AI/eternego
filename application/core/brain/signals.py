"""Signals — classification helpers for threads.

classify(threads)   split into (active, inactive) based on last signal role.
"""

from application.core.brain.data import Thread


def classify(threads: list[Thread]) -> tuple[list[Thread], list[Thread]]:
    """Split threads into (active, inactive).

    Active:   last signal is from user — thread still needs a response.
    Inactive: last signal is from assistant — thread has been addressed.
    """
    active, inactive = [], []
    for t in threads:
        if t.signals and t.signals[-1].prompt.role == "assistant":
            inactive.append(t)
        else:
            active.append(t)
    return active, inactive


