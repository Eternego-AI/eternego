"""Calendar — get all pending scheduled events."""

from application.core.brain.data import Tool


class _Calendar(Tool):
    name = "calendar"
    requires_permission = False
    meaning_only = True
    instruction = (
        "Tool: calendar\n"
        "Get all pending scheduled events.\n"
        "Params: {}"
    )

    def execution(self):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.debug("calendar: reading scheduled events", {"persona_id": persona.id})
            destiny_dir = paths.destiny(persona.id)
            entries = paths.read_files_matching(persona.id, destiny_dir, "schedule-*.md")
            if not entries:
                return "no scheduled events found"
            return "Scheduled events:\n" + "\n---\n".join(entries)
        return _run


tool = _Calendar()
