"""Shell — how to run shell commands via the shell trait."""

from application.core.brain.data import Skill


class _ShellSkill(Skill):
    name = "shell"
    description = (
        "Provides commands and patterns for running shell operations, "
        "managing files, and working within the workspace."
    )

    def execution(self):
        def _doc(persona):
            from application.core import paths
            workspace = str(paths.home(persona.id) / "workspace")
            return f"""# Shell

Use the `shell` trait to run commands:

```json
{{"trait": "shell", "params": {{"command": "your command here"}}}}
```

## Workspace

Write all files to: {workspace}

## Common Patterns

| Task | Command |
|---|---|
| Read a file | `cat /path/to/file` |
| List directory | `ls -la /path` |
| Write to workspace | `echo "content" > {workspace}/file.txt` |
| Append to file | `echo "line" >> {workspace}/file.txt` |
| Current date/time | `date` |
| Check if installed | `which command_name` |
| Find files | `find /path -name "*.ext"` |
| Disk usage | `du -sh /path` |
| Running processes | `ps aux | grep name` |

## Multi-step Workflows

When a shell result shapes what you say next, use `reflect` after the shell step. This seeds the next tick with the actual output so the following cycle can respond with real data rather than guessing.

## Caution

Never use shell to directly modify these persona files:

`context.md`, `person.md`, `traits.md`, `permissions.md`

Use the traits for those instead."""
        return _doc


skill = _ShellSkill()
