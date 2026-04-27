"""Meaning — troubleshooting."""

from application.core import paths
from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Something is wrong in software or the machine"

    def path(self) -> str:
        meanings_dir = paths.meanings(self.persona.id)
        custom_meanings = []
        if meanings_dir.exists():
            custom_meanings = [f.stem for f in sorted(meanings_dir.glob("*.py"))]
        custom_list = "\n".join(f"- {name}" for name in custom_meanings) if custom_meanings else "(none)"

        recent_health = paths.read_jsonl(paths.health_log(self.persona.id))[-5:]
        if recent_health:
            health_lines = []
            for entry in recent_health:
                when = entry.get("time", "?")
                loop = entry.get("loop_number", "?")
                faults = entry.get("fault_count", 0)
                providers = ", ".join(entry.get("fault_providers", [])) or "none"
                health_lines.append(f"- {when} (loop {loop}) — {faults} fault(s); providers: {providers}")
            health_section = "\n".join(health_lines)
        else:
            health_section = "(no health checks logged yet)"

        return (
            "Something is wrong — repeated tool errors in the conversation, the same response "
            "repeating, memory full of failed attempts, a tool or service that keeps failing, "
            "or the machine itself not cooperating. Identify what has gone wrong and fix what "
            "you can reach.\n\n"
            "Common causes and how to handle each:\n"
            "- A custom meaning is producing output your thinking model cannot handle — use "
            "`remove_meaning` with its name.\n"
            "- Memory is full of failed attempts or repeated apologies with no useful state — "
            "use `clear_memory`.\n"
            "- A service or dependency on the machine is missing or misbehaving and there is "
            "nothing you can change from here — tell the person with `say` so they can fix it.\n"
            "- Nothing you can reach — use `stop` until the person is back.\n\n"
            f"## Recent health checks\n\n{health_section}\n\n"
            f"## Custom meanings you can remove\n\n{custom_list}\n\n"
            "Built-in meanings cannot be removed."
        )
