"""Brain meanings — recognized situations the persona knows how to handle.

Two layers, one shape:

- `builtin(persona)` — meanings that ship with Eternego. The `_BUILTIN`
  map below holds `{intention: stem}`; each body lives next to this
  module as `{stem}.md` (pure Markdown, no H1 wrapper). Built-in stems
  are stable named identifiers that ship with the codebase.

- `custom(persona)` — persona-specific meanings written by `learn` or
  `reflect`. The per-persona `{intention: file_id}` map at
  `paths.learned(...)` carries the metadata; bodies live in
  `meanings/{file_id}.md`. File IDs for new custom meanings are opaque
  UUIDs — the cognitive layer never sees them, only the intention text.

Same file shape both ways — body is whatever was written, no parsing.
Both layers list by intention in Ego's identity prompt; the path text is
injected via `tools.load_instruction(intention=...)` when the persona
asks for guidance.

Writes to `learned.json` happen at the call sites (reflect, learn). Each
caller reads the catalog once, mutates the dict in-memory, writes it
back once. The shape is `{intention_text: file_id}` and dict assignment
is the natural primitive — no helper needed.
"""

import uuid
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
    """Every built-in meaning. The `_BUILTIN` map below carries
    `{intention: stem}`. Stems are stable named identifiers shipping with
    the codebase; bodies live as `{stem}.md` next to this module."""
    _BUILTIN: dict[str, str] = {
        "Any type of conversation, there is nothing to do but talk": "chatting",
        "Working with files and directories on the machine": "exploring_filesystem",
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
    """Persona-specific meanings written to disk by learn or reflect.

    Source of truth is the per-persona map at `paths.learned(persona.id)`,
    which carries `{intention: file_id}` entries. The meaning's body is
    the full content of `meanings/{file_id}.md` — pure Markdown, no H1
    wrapper, no internal parsing. Whatever was written is what the
    persona reads when she loads the instruction.
    """
    out: dict[str, Meaning] = {}
    persona_dir = paths.meanings(persona.id)
    if not persona_dir.exists():
        return out
    intention_to_id = paths.read_json(paths.learned(persona.id)) or {}
    for intention, file_id in intention_to_id.items():
        meaning_file = persona_dir / f"{file_id}.md"
        if not meaning_file.exists():
            continue
        body = paths.read(meaning_file).strip()
        out[file_id] = Meaning(file_id, intention, body)
    return out


def save_lesson(persona_id: str, intention: str, body: str) -> str:
    """Write a lesson to disk under an opaque UUID; return the UUID.

    Lessons are teacher-authored principles (raw form). Filename is a
    UUID — the cognitive layer never references lesson files by name,
    so the name only needs to be unique on disk. Reflect's persona-
    authored procedures don't go through save_lesson (they aren't
    teacher-authored), so reflect generates its own UUID inline.
    """
    intention = (intention or "").strip()
    body = (body or "").strip()
    if not intention:
        raise ValueError("lesson intention is empty")
    if not body:
        raise ValueError("lesson body is empty")
    file_id = str(uuid.uuid4())
    full = f"# {intention}\n\n{body}\n"
    paths.save_as_string(paths.lessons(persona_id) / f"{file_id}.md", full)
    return file_id
