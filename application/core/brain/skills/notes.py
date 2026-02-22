"""Notes — how to take and retrieve structured notes for the person."""

name = "notes"
summary = "Knows how to write, list, read, and search the person's notes using the filesystem."


def skill(persona) -> str:
    notes_dir = str(persona.storage_dir / "notes")
    return f"""# Notes

Take and retrieve structured notes for the person using the filesystem.

## Write a Note

```
cat > {notes_dir}/YYYY-MM-DD-title.md << 'EOF'
# Title

Content here.
EOF
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

```
ls -1t {notes_dir}/
```

## Read a Note

```
cat {notes_dir}/YYYY-MM-DD-title.md
```

## Search Notes

```
grep -rl "keyword" {notes_dir}/
```

## Tips

- Use ISO date prefix (YYYY-MM-DD) so notes sort chronologically
- Keep filenames short and lowercase with hyphens
- Summarise what you saved rather than printing raw file contents"""
