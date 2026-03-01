"""Grant Permission — records a persistent permission grant to the permissions file.

Use when the person has granted broad or significant permission that should be
remembered across sessions. Save the statement as the person expressed it.
Include the signal_id of the message where permission was given.
"""

from application.core.brain.data import Tool


class _GrantPermission(Tool):
    name = "grant_permission"
    requires_permission = False
    description = (
        "Records a persistent permission grant. Use when the person grants broad or "
        "significant permission that should be remembered across sessions."
    )
    instruction = (
        "Tool: grant_permission\n"
        "Persist a permission grant to the permissions file.\n"
        'Params: {"signal_id": "id of the signal where permission was given", '
        '"statement": "the permission as the person expressed it"}'
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
            data["granted"].append(entry)
            filesystem.write(p, json.dumps(data, indent=2))
            return f"permission grant recorded"
        return _run


tool = _GrantPermission()
