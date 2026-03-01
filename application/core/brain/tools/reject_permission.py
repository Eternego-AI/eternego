"""Reject Permission — records a persistent permission rejection to the permissions file.

Use when the person has denied broad or significant permission that should be
remembered across sessions. Save the statement as the person expressed it.
Include the signal_id of the message where permission was denied.
"""

from application.core.brain.data import Tool


class _RejectPermission(Tool):
    name = "reject_permission"
    requires_permission = False
    description = (
        "Records a persistent permission rejection. Use when the person denies broad or "
        "significant permission that should be remembered across sessions."
    )
    instruction = (
        "Tool: reject_permission\n"
        "Persist a permission rejection to the permissions file.\n"
        'Params: {"signal_id": "id of the signal where permission was denied", '
        '"statement": "the rejection as the person expressed it"}'
    )

    def execution(self, signal_id="", statement=""):
        async def _run(persona):
            import json
            from application.core import paths
            from application.core.brain import mind as mind_module
            from application.platform import filesystem

            m = mind_module.get(persona.id)
            signal = next((s for s in (m.signals if m else []) if s.id == signal_id), None)

            entry = statement
            if signal:
                entry += f" (signal: {signal_id}, at: {signal.created_at.strftime('%Y-%m-%d %H:%M')})"

            p = paths.permissions(persona.id)
            raw = paths.read(p)
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {}
            data.setdefault("granted", [])
            data.setdefault("rejected", [])
            data["rejected"].append(entry)
            filesystem.write(p, json.dumps(data, indent=2))
            return "permission rejection recorded"
        return _run


tool = _RejectPermission()
