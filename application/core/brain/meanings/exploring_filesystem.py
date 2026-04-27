"""Meaning — exploring_filesystem."""

from application.core import paths
from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Working with files and directories on the machine"

    def path(self) -> str:
        workspace = str(paths.workspace(self.persona.id))
        home = str(paths.home(self.persona.id))
        return (
            "Work with files and directories. Your workspace is where you are free to create, "
            f"edit, and delete anything: `{workspace}`. Your home is readable but not "
            f"modifiable: `{home}`. For paths outside those, check your granted permissions "
            "before destructive or sensitive operations; if they are not granted, ask with "
            "`say`.\n\n"
            "Reach for `tools.filesystem.read`, `tools.filesystem.write`, "
            "`tools.filesystem.append`, `tools.filesystem.delete`, `tools.filesystem.create_dir`, "
            "`tools.filesystem.delete_dir`, or `tools.filesystem.copy_dir` for file operations. "
            "Use `tools.OS.execute_on_sub_process` with a shell `command` for listing or "
            "anything else the filesystem tools don't cover. After the TOOL_RESULT comes back "
            "on the next cycle, report with `say`."
        )
