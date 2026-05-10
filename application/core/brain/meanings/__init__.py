"""Brain meanings — recognized situations the persona knows how to handle.

Two layers, one shape:

- `builtin(persona)` — meanings that ship with Eternego. The `_BUILTIN`
  map below holds `{stem: intention}`; each body lives next to this
  module as `{stem}.md` (pure Markdown, no H1 wrapper). Stems are the
  persona-facing names used in selectors (`meanings.<stem>`).

- `custom(persona)` — persona-specific meanings written by `learn`. The
  per-persona `{intention: stem}` map at `paths.learned(...)` carries the
  metadata; bodies live in `meanings/{stem}.md` (also pure Markdown).

Same file shape both ways — body is whatever was written, no parsing.
Both layers list by intention in Ego's identity prompt; the path text is
injected by decide only when a meaning is selected.
"""

import re
from pathlib import Path

from application.core import paths


_BUILTIN_DIR = Path(__file__).parent


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
    """Every built-in meaning. The `_BUILTIN` map below mirrors the shape
    of the per-persona `learned.json` for custom meanings: `{intention:
    stem}`. Stems are the file names of the body markdown next to this
    module and the persona-facing names used in selectors."""
    _BUILTIN: dict[str, str] = {
        "Any type of conversation, there is nothing to do but talk": "chatting",
        "Working with files and directories on the machine": "exploring_filesystem",
        "Noticing something worth keeping that does not belong in another file": "noting",
        "Looking back at past conversations or scheduled events": "recalling",
        "Saving a reminder or event for a future moment, or responding when one has come due": "scheduling",
        "Something is wrong in software or the machine": "troubleshooting",
    }
    out: dict[str, Meaning] = {}
    for intention, stem in _BUILTIN.items():
        body_file = _BUILTIN_DIR / f"{stem}.md"
        body = paths.read(body_file).strip() if body_file.exists() else ""
        out[stem] = Meaning(stem, intention, body)
    return out


def custom(persona) -> dict[str, Meaning]:
    """Persona-specific meanings written to disk by learn.

    Source of truth is the per-persona map at `paths.learned(persona.id)`,
    which carries `{intention: stem}` entries. The meaning's body is the
    full content of `meanings/{stem}.md` — pure Markdown, no H1 wrapper,
    no internal parsing. Whatever the persona learned is what decide reads.
    """
    out: dict[str, Meaning] = {}
    persona_dir = paths.meanings(persona.id)
    if not persona_dir.exists():
        return out
    intention_to_stem = paths.read_json(paths.learned(persona.id)) or {}
    for intention, stem in intention_to_stem.items():
        meaning_file = persona_dir / f"{stem}.md"
        if not meaning_file.exists():
            continue
        body = paths.read(meaning_file).strip()
        out[stem] = Meaning(stem, intention, body)
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


