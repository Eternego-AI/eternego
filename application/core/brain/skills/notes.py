"""Notes — how to take and retrieve structured notes for the person."""

from application.core.brain.data import Skill


class _NotesSkill(Skill):
    name = "notes"
    description = (
        "Provides commands for writing, reading, listing, and searching "
        "the person's notes using the filesystem."
    )

    def execution(self):
        def _doc(persona):
            from application.core import paths
            notes_dir = str(paths.home(persona.id) / "notes")
            return f"""# Notes

Take and retrieve structured notes for the person using the `shell` trait.

## Write a Note

```json
{{"tool": "shell", "params": {{"command": "cat > {notes_dir}/YYYY-MM-DD-title.md << 'EOF'\\n# Title\\n\\nContent here.\\nEOF"}}}}
```

Or use Python to get today's date automatically (see `python` skill):

```python
from datetime import date
today = date.today().isoformat()
title = "meeting-recap"
path = f"{notes_dir}/{{today}}-{{title}}.md"
with open(path, "w") as f:
    f.write("# Meeting Recap\\n\\nContent here.\\n")
print(f"Saved to {{path}}")
```

## List Notes

```json
{{"tool": "shell", "params": {{"command": "ls -1t {notes_dir}/"}}}}
```

## Read a Note

```json
{{"tool": "shell", "params": {{"command": "cat {notes_dir}/YYYY-MM-DD-title.md"}}}}
```

## Search Notes

```json
{{"tool": "shell", "params": {{"command": "grep -rl \\"keyword\\" {notes_dir}/"}}}}
```

## Tips

- Use ISO date prefix (YYYY-MM-DD) so notes sort chronologically
- Keep filenames short and lowercase with hyphens
- When writing or saving a note, `say` can confirm directly — no reflect needed
- When reading, listing, or searching notes, use `reflect` with the result so the next tick can compose a response from the actual content rather than guessing"""
        return _doc


skill = _NotesSkill()
