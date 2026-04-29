"""Brain meanings — recognized situations the persona knows how to handle.

Each meaning is one situation, expressed as a markdown file:

    # {intention}

    {path text — the prose the persona reads while acting}

The meaning's `name` is the file's stem (lowercase ASCII + underscore).
`intention` is one short gerund phrase. `path` is the multi-paragraph
prose that addresses the persona in second person and tells her how to
handle the situation.

Two layers:

- `builtin(persona)` — meanings that ship with Eternego, read from
  `application/core/brain/meanings/*.md`.
- `custom(persona)` — persona-specific meanings written by `learn`,
  read from the persona's own `meanings/` directory.

Both are listed by intention in Ego's identity prompt; the path text
is injected by `decide` only when a meaning is selected.
"""

import re
from pathlib import Path

from application.core import paths
from application.platform import filesystem, logger


_BUILTIN_DIR = Path(__file__).parent


# Basic meanings: states the persona is in (single ability + a say), not
# procedures she runs. Loaded with full path text into Ego's identity so
# she's continuously aware of her modes of being-with-the-person. The rest
# of the built-ins are orchestrating — listed by intention only and have
# their path injected by decide on selection.
BASIC = ["asking", "chatting", "noting", "recalling", "scheduling"]


class Meaning:
    """A recognized situation. Holds intention text and path prose."""

    def __init__(self, name: str, intention: str, path: str):
        self.name = name
        self._intention = intention
        self._path = path

    def intention(self) -> str:
        return self._intention

    def path(self) -> str:
        return self._path


def builtin(persona) -> dict[str, Meaning]:
    """Every built-in meaning, read from this package's directory."""
    out: dict[str, Meaning] = {}
    for f in sorted(_BUILTIN_DIR.glob("*.md")):
        m = _read_meaning(f, f.stem)
        if m is not None:
            out[f.stem] = m
    return out


def custom(persona) -> dict[str, Meaning]:
    """Persona-specific meanings written to disk by learn."""
    out: dict[str, Meaning] = {}
    persona_dir = paths.meanings(persona.id)
    if not persona_dir.exists():
        return out
    for f in sorted(persona_dir.glob("*.md")):
        m = _read_meaning(f, f.stem)
        if m is not None:
            out[f.stem] = m
    return out


def load(persona, name: str) -> Meaning | None:
    """Load one custom meaning by name — used right after save_meaning."""
    f = paths.meanings(persona.id) / f"{name}.md"
    if not f.exists():
        return None
    return _read_meaning(f, name)


def save_meaning(persona_id: str, name: str, intention: str, path: str) -> str:
    """Write a new persona-specific meaning to disk; return sanitized name."""
    name = re.sub(r"[^\w-]", "", name.lower().replace(" ", "-"))[:60]
    if not name:
        raise ValueError("meaning name is empty after sanitization")
    intention = (intention or "").strip()
    path = (path or "").strip()
    if not intention:
        raise ValueError("intention is empty")
    if not path:
        raise ValueError("path is empty")
    body = f"# {intention}\n\n{path}\n"
    filesystem.write(paths.meanings(persona_id) / f"{name}.md", body)
    return name


def _read_meaning(file: Path, name: str) -> Meaning | None:
    try:
        text = file.read_text(encoding="utf-8")
        intention, body = _parse_md(text)
    except (OSError, ValueError) as e:
        logger.warning("Meaning failed to load", {"file": str(file), "error": str(e)})
        return None
    return Meaning(name=name, intention=intention, path=body)


def _parse_md(text: str) -> tuple[str, str]:
    """First non-empty line must be `# {intention}`. Rest is the path body."""
    lines = text.splitlines()
    intention = None
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("# "):
            raise ValueError(f"first non-empty line must be `# <intention>`, got: {stripped[:60]}")
        intention = stripped[2:].strip()
        body_start = i + 1
        break
    if not intention:
        raise ValueError("missing intention heading")
    body = "\n".join(lines[body_start:]).strip()
    if not body:
        raise ValueError("missing path body")
    return intention, body
