"""Clarification — guidance on when and how to ask the person for more information."""

from application.core.brain.data import Skill


class _Clarification(Skill):
    name = "clarification"
    description = (
        "Explains when and how to ask the person for clarification. "
        "Load when you are uncertain about intent and need guidance before acting."
    )

    def execution(self):
        def _doc(persona):
            return """# Asking for Clarification

Ask one focused question when you genuinely need more information before you can act effectively.

## When to clarify

- The intent is ambiguous and acting on the wrong assumption would waste effort or cause harm.
- A key detail is missing and you cannot reasonably infer it.
- You are about to take an irreversible action and want to confirm.

## When NOT to clarify

- When you can make a reasonable inference — act and mention your assumption.
- When the request is clear enough to attempt — try it and offer to adjust.
- Do not ask multiple clarifying questions at once. Pick the most important one."""
        return _doc


skill = _Clarification()
