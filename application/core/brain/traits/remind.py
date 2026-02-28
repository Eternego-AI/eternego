"""Remind — set a reminder at a specific datetime."""

from application.core.brain.data import Trait


class _Remind(Trait):
    name = "remind"
    requires_permission = False
    description = (
        "Sets a reminder at a specific date and time. "
        "Use when the person wants to be reminded of something at a specific moment."
    )
    instruction = (
        "Trait: remind\n"
        "Set a reminder at a specific datetime.\n"
        'Params: {"trigger": "YYYY-MM-DD HH:MM", "content": "what to be reminded of"}'
    )

    def execution(self, trigger="", content=""):
        async def _run(persona):
            import secrets
            from datetime import datetime
            from application.core import paths
            from application.platform import logger
            logger.debug("remind: saving reminder", {"persona_id": persona.id, "trigger": trigger, "content": content[:80]})
            if not trigger:
                return "no trigger provided — use clarify to ask when this reminder should fire"
            try:
                datetime.strptime(trigger, "%Y-%m-%d %H:%M")
            except ValueError:
                return f"invalid trigger format '{trigger}' — must be YYYY-MM-DD HH:MM"
            if not content:
                return "no content provided — use clarify to ask what to be reminded about"
            paths.save_destiny_entry(persona.id, "reminder", trigger, secrets.token_hex(4), content)
            return f"reminder set: {trigger} — {content}"
        return _run


trait = _Remind()
