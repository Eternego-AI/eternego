"""Python — how to write and run Python scripts via the shell trait."""

from application.core.brain.data import Skill


class _PythonSkill(Skill):
    name = "python"
    description = (
        "Provides patterns for writing and running Python scripts "
        "for calculations, file processing, and automation."
    )

    def execution(self):
        def _doc(persona):
            from application.core import paths
            workspace = str(paths.home(persona.id) / "workspace")
            return f"""# Python

Write a script to workspace then run it — two `shell` trait calls:

**1. Write the script:**
```json
{{"trait": "shell", "params": {{"command": "cat > {workspace}/script.py << 'EOF'\\n# your code here\\nprint(\\"result\\")\\nEOF"}}}}
```

**2. Run it:**
```json
{{"trait": "shell", "params": {{"command": "python3 {workspace}/script.py"}}}}
```

The output is returned as the trait result.

## Tips

- Write all file I/O inside scripts to `{workspace}/`
- Print results to stdout — that is what shell captures
- For one-off calculations: `python3 -c "print(2 + 2)"`
- Install a missing package: `pip install --quiet package_name`
- Clean up when done: `rm {workspace}/script.py`
- After running a script that produces output you need to report, use `reflect` to seed the next tick with the actual result rather than guessing it at plan time

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
        return _doc


skill = _PythonSkill()
