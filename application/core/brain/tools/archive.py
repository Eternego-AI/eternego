"""Archive — write a completed thread to history."""

from application.core.brain.data import Tool


class _Archive(Tool):
    name = "archive"
    requires_permission = False
    description = (
        "Archives a completed conversation thread to long-term history. "
        "Use when a thread is clearly finished and no longer needs to stay in active memory. "
        "Provide the signal IDs that belong to the thread, a short title, and a one-sentence recap."
    )
    instruction = (
        "Tool: archive\n"
        "Archive a completed thread to history.\n"
        'Params: {"signal_ids": ["id1", "id2", ...], "title": "short thread title", "recap": "one sentence summary"}'
    )

    def execution(self, signal_ids=None, title="", recap=""):
        async def _run(persona):
            from application.core.brain import mind as mind_module
            from application.core import paths
            from application.platform import datetimes, logger
            logger.debug("archive: archiving thread", {"persona_id": persona.id, "title": title, "signals": len(signal_ids or [])})
            m = mind_module.get(persona.id)
            if m is None:
                return "failed: mind not loaded"
            ids = set(signal_ids or [])
            signals = [s for s in m.signals if s.id in ids]
            if not signals:
                return "failed: no matching signals found"
            lines = []
            for s in signals:
                channel = f" via {s.channel.name}" if s.channel else ""
                time = s.created_at.strftime("%Y-%m-%d %H:%M UTC")
                lines.append(f"[{s.prompt.role}{channel} at {time}]: {s.prompt.content}")
            timestamp = datetimes.date_stamp(datetimes.now())
            paths.add_history_entry(persona.id, title or "untitled", "\n\n".join(lines))
            paths.add_history_briefing(
                persona.id,
                "| Date | Recap | File |",
                f"| {timestamp} | {recap} | {title}-{timestamp}.md |",
            )
            m.signals = [s for s in m.signals if s.id not in ids]
            return f"archived '{title}' ({len(signals)} signals)"
        return _run


tool = _Archive()
