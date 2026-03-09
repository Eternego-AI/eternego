"""Reminder — get all pending reminders."""

from application.core.brain.data import Tool


class _Reminder(Tool):
    name = "check_reminders"
    requires_permission = False
    meaning_only = True
    instruction = (
        "Tool: check_reminders\n"
        "List all pending reminders.\n"
        "Params: {}"
    )

    def execution(self):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.debug("reminder: reading reminders", {"persona_id": persona.id})
            destiny_dir = paths.destiny(persona.id)
            entries = paths.read_files_matching(persona.id, destiny_dir, "reminder-*.md")
            if not entries:
                return "no reminders found"
            return "Reminders:\n" + "\n---\n".join(entries)
        return _run


tool = _Reminder()
