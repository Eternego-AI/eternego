"""Reminder — get all pending reminders."""

from application.core.brain.data import Trait


class _Reminder(Trait):
    name = "reminder"
    requires_permission = False
    description = (
        "Retrieves all pending reminders. "
        "Use when you need to see what reminders are set or to identify ones that are due."
    )
    instruction = (
        "Trait: reminder\n"
        "Get all pending reminders.\n"
        "Params: {}"
    )

    def execution(self):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.info("reminder: reading reminders", {"persona_id": persona.id})
            destiny_dir = paths.destiny(persona.id)
            entries = paths.read_files_matching(persona.id, destiny_dir, "reminder-*.md")
            if not entries:
                return "no reminders found"
            return "Reminders:\n" + "\n---\n".join(entries)
        return _run


trait = _Reminder()
