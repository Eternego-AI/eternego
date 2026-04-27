"""Pulse — `hint()` returns a system prompt for the current phase.

Pulse is otherwise a thin holder of phase + worker; only `hint()` carries
behavior worth covering."""

from application.core.brain.pulse import Phase, Pulse


def test_hint_returns_a_system_prompt_for_the_current_phase():
    p = Pulse(worker=None)
    p.phase = Phase.MORNING
    hints = p.hint()
    assert len(hints) == 1
    assert hints[0].role == "system"
    assert hints[0].content
