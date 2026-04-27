"""Mind — the persona's thinking apparatus.

A factory that binds the cognitive functions to a Living instance, returning
the cycle as a list of `(name, callable)` pairs. Clock walks this list every
beat.

Lives in its own module (rather than alongside Living in agents.py) so that
agents.py does not need to import the functions package — which is what kept
us in a circular import. Functions can now type-hint `Living` directly,
because agents.py is import-side-effect-free for the function modules.
"""

from application.core.brain import functions
from application.core.agents import Living


def mind(living: Living) -> list:
    """Return the cycle: (name, callable) pairs in cognitive order.

    Each callable is a closure over Living — Clock invokes them with no args.
    Cognitive type per function is fixed (realize: think/vision; recognize,
    decide, reflect: think; learn: escalate; archive: think/vision)."""
    return [
        ("realize",    lambda: functions.realize(living)),
        ("recognize",  lambda: functions.recognize(living)),
        ("learn",      lambda: functions.learn(living)),
        ("decide",     lambda: functions.decide(living)),
        ("reflect",    lambda: functions.reflect(living)),
        ("archive",    lambda: functions.archive(living)),
    ]
