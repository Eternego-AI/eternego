"""Pulse — `hint()` returns a system prompt for the current phase.

Pulse is otherwise a thin holder of phase + worker + signals; only
`hint()` is covered here."""

from application.core.brain.pulse import Phase, Pulse
from application.core.data import Model, Persona


def test_hint_returns_a_system_prompt_for_the_current_phase():
    persona = Persona(id="t", name="T", thinking=Model(name="m", url="not used"))
    p = Pulse(worker=None, persona=persona)
    p.phase = Phase.MORNING
    hints = p.hint()
    assert len(hints) == 1
    assert hints[0].role == "system"
    assert hints[0].content
    p.dispose()
