"""Python — how to write and run Python scripts via the act ability."""

name = "python"
summary = "Knows how to write Python scripts to the workspace and execute them for calculations, file processing, and automation."


def skill(persona) -> str:
    from application.core import paths
    workspace = str(paths.home(persona.id) / "workspace")
    return f"""# Python

Write a script to workspace then run it — two `act` calls:

**1. Write the script:**
```
cat > {workspace}/script.py << 'EOF'
# your code here
print("result")
EOF
```

**2. Run it:**
```
python3 {workspace}/script.py
```

The output is returned to you by `act`.

## Tips

- Write all file I/O inside scripts to `{workspace}/`
- Print results to stdout — that is what `act` captures
- For one-off calculations, use `python3 -c "print(2 + 2)"` directly
- Install a missing package: `pip install --quiet package_name`
- Clean up when done: `rm {workspace}/script.py`

## Useful Patterns

Parse JSON from a previous step:
```python
import json
with open("{workspace}/search.json") as f:
    data = json.load(f)
print(data["AbstractText"])
```

Work with dates:
```python
from datetime import datetime, timedelta
print((datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))
```"""
