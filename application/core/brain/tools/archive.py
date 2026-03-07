"""Archive — write a completed thread to history."""

from application.core.brain.data import Tool


class _Archive(Tool):
    name = "archive"
    requires_permission = False
    description = (
        "Archives a completed conversation thread to long-term history. "
        "Use when a thread is clearly finished and no longer needs to stay in active memory. "
        "Provide the occurrence IDs that belong to the thread, a short title, and a one-sentence recap."
    )
    instruction = (
        "Tool: archive\n"
        "Archive a completed thread to history.\n"
        'Params: {"occurrence_ids": ["id1", "id2", ...], "title": "short thread title", "recap": "one sentence summary"}'
    )

    def execution(self, occurrence_ids=None, title="", recap=""):
        async def _run(persona):
            from application.core.brain import mind as mind_module
            from application.core import paths
            from application.platform import datetimes, logger
            logger.debug("archive: archiving thread", {"persona_id": persona.id, "title": title, "occurrences": len(occurrence_ids or [])})
            m = mind_module.get(persona.id)
            if m is None:
                return "failed: mind not loaded"
            ids = set(occurrence_ids or [])
            occurrences = [o for o in m.occurrences if o.id in ids]
            if not occurrences:
                return "failed: no matching occurrences found"
            lines = []
            for o in occurrences:
                time = o.created_at.strftime("%Y-%m-%d %H:%M UTC")
                lines.append(f"[at {time}]")
                lines.append(f"  cause [{o.cause.role}]: {o.cause.content}")
                lines.append(f"  effect [{o.effect.role}]: {o.effect.content}")
            timestamp = datetimes.date_stamp(datetimes.now())
            paths.add_history_entry(persona.id, title or "untitled", "\n".join(lines))
            paths.add_history_briefing(
                persona.id,
                "| Date | Recap | File |",
                f"| {timestamp} | {recap} | {title}-{timestamp}.md |",
            )
            m.occurrences = [o for o in m.occurrences if o.id not in ids]
            return f"archived '{title}' ({len(occurrences)} occurrences)"
        return _run


tool = _Archive()
