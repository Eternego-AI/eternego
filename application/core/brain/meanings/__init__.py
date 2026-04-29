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
        sections = paths.md_dict(f)
        if sections:
            intention, body = next(iter(sections.items()))
            out[f.stem] = Meaning(f.stem, intention, body)
    return out


def custom(persona) -> dict[str, Meaning]:
    """Persona-specific meanings written to disk by learn."""
    out: dict[str, Meaning] = {}
    persona_dir = paths.meanings(persona.id)
    if not persona_dir.exists():
        return out
    for f in sorted(persona_dir.glob("*.md")):
        sections = paths.md_dict(f)
        if sections:
            intention, body = next(iter(sections.items()))
            out[f.stem] = Meaning(f.stem, intention, body)
    return out


def save_lesson(persona_id: str, intention: str, path: str) -> str:
    """Write a frontier-authored lesson to disk; return its slugified id."""
    intention = (intention or "").strip()
    path = (path or "").strip()
    if not intention:
        raise ValueError("lesson intention is empty")
    if not path:
        raise ValueError("lesson path is empty")
    lesson_id = re.sub(r"[^\w-]", "", intention.lower().replace(" ", "_"))[:60]
    lesson_id = lesson_id.strip("_-")
    if not lesson_id:
        raise ValueError("lesson id is empty after sanitization")
    body = f"# {intention}\n\n{path}\n"
    paths.save_as_string(paths.lessons(persona_id) / f"{lesson_id}.md", body)
    return lesson_id


