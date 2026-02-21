# Notes

Take and retrieve structured notes for the person using the filesystem.

## Write a Note

```
cat > {workspace}/../notes/YYYY-MM-DD-title.md << 'EOF'
# Title

Content here.
EOF
```

Or use Python to get today's date automatically (see `python` skill):

```python
from datetime import date
today = date.today().isoformat()
title = "meeting-recap"
path = f"{workspace}/../notes/{today}-{title}.md"
with open(path, "w") as f:
    f.write("# Meeting Recap\n\nContent here.\n")
print(f"Saved to {path}")
```

## List Notes

```
ls -1t {workspace}/../notes/
```

## Read a Note

```
cat {workspace}/../notes/YYYY-MM-DD-title.md
```

## Search Notes

```
grep -rl "keyword" {workspace}/../notes/
```

## Tips

- Use ISO date prefix (YYYY-MM-DD) so notes sort chronologically
- Keep filenames short and lowercase with hyphens
- Summarise what you saved rather than printing raw file contents
