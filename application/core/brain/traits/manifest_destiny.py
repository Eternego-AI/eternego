"""Manifest destiny — archive a destiny entry to history and mark it done."""

from application.core.brain.data import Trait


class _ManifestDestiny(Trait):
    name = "manifest_destiny"
    requires_permission = False
    description = (
        "Archives a destiny entry (scheduled event or reminder) to history and removes it from destiny. "
        "Use when a scheduled event or reminder has been delivered or completed."
    )
    instruction = (
        "Trait: manifest_destiny\n"
        "Archive a destiny entry to history and mark it as done.\n"
        'Params: {"filename": "the destiny entry filename"}'
    )

    def execution(self, filename=""):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger, filesystem
            logger.info("manifest_destiny: manifesting entry", {"persona_id": persona.id, "filename": filename})
            if not filename:
                return "no filename provided"
            destiny_dir = paths.destiny(persona.id)
            entry_path = destiny_dir / filename
            content = paths.read(entry_path)
            if not content:
                return f"entry not found: {filename}"
            paths.add_history_entry(persona.id, "destiny", content)
            filesystem.delete(entry_path)
            return f"manifested: {filename}"
        return _run


trait = _ManifestDestiny()
