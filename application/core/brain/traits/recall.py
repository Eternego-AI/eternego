"""Recall — load a specific past conversation from history by filename."""

from application.core.brain.data import Trait


class _Recall(Trait):
    name = "recall"
    requires_permission = False
    description = (
        "Loads a specific past conversation from history by filename. "
        "Use after seek_history has identified the right file to retrieve the full content."
    )
    instruction = (
        "Trait: recall\n"
        "Load a specific past conversation from history by filename.\n"
        'Params: {"filename": "the filename from the history briefing"}'
    )

    def execution(self, filename=""):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.debug("recall: loading history file", {"persona_id": persona.id, "filename": filename})
            if not filename:
                return "no filename provided"
            content = paths.read(paths.history(persona.id) / filename)
            if not content:
                return f"file not found: {filename}"
            return content
        return _run


trait = _Recall()
