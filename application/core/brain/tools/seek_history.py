"""Seek history — load the history briefing to find past conversations."""

from application.core.brain.data import Tool


class _SeekHistory(Tool):
    name = "seek_history"
    requires_permission = False
    meaning_only = True
    instruction = (
        "Tool: seek_history\n"
        "Load the history briefing to find past conversations.\n"
        "Params: {}"
    )

    def execution(self):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.debug("seek_history: loading history briefing", {"persona_id": persona.id})
            return paths.read_history_brief(persona.id, "(no history yet)")
        return _run


tool = _SeekHistory()
