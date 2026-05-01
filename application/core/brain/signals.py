"""Brain signals — typed Signal classes for cognitive observability.

The brain layer dispatches its observability through these classes rather
than untyped strings. Subscribers filter by `isinstance(signal, Tick)` or
`isinstance(signal, BrainFault)` instead of string-matching titles, so
renaming a stage or tweaking a label can never silently break a listener.

Each class extends one of the platform Signal kinds (Plan = intention,
Event = outcome) so the existing dispatch and bus infrastructure carries
them unchanged.
"""

from application.platform.observer import Event, Plan


class Tick(Plan):
    """A cognitive function is about to run.

    title:   the function name (e.g. "realize", "recognize", "decide")
    details: {"persona": Persona}
    """
    pass


class Tock(Event):
    """A cognitive function has completed.

    title:   the function name
    details: {"persona": Persona}
    """
    pass


class BrainFault(Event):
    """A cognitive function raised an exception during clock.run.

    title:   the function name where the fault occurred
    details: {
        "persona": Persona,
        "provider": str | None,
        "url": str | None,
        "model_name": str | None,
        "error": str,
    }
    """
    pass


class CapabilityRun(Event):
    """Clock's executor ran a tool or ability declared by a function.

    title:   the full selector, e.g. "tools.OS.execute"
             or "abilities.save_destiny"
    details: {
        "persona": Persona,
        "args": dict,
        "status": "ok" | "error",
        "result": Any,
    }
    """
    pass
