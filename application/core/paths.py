"""Paths — application directory layout."""

import os
from pathlib import Path

from application.platform import filesystem, logger, objects, git, crypto, datetimes


def eternego_home() -> Path:
    """Root directory for all Eternego data."""
    custom = os.environ.get("ETERNEGO_HOME")
    if custom:
        return Path(custom)
    return Path.home() / ".eternego"


def personas_home() -> Path:
    """Root directory for all persona storage."""
    return eternego_home() / "personas"


def home(persona_id: str) -> Path:
    """Root directory for a specific persona."""
    return eternego_home() / "personas" / persona_id / "home"


def workspace(persona_id: str) -> Path:
    """Path to the workspace directory for that persona."""
    return eternego_home() / "personas" / persona_id / "workspace"


def conversation(persona_id: str) -> Path:
    """Path to the conversation.jsonl file for that persona."""
    return home(persona_id) / "conversation.jsonl"


def persona_identity(persona_id: str) -> Path:
    """Path to the config.json file for that persona."""
    return home(persona_id) / "config.json"


def person_identity(persona_id: str) -> Path:
    """Path to the person.md file for that persona."""
    return home(persona_id) / "person.md"


def person_traits(persona_id: str) -> Path:
    """Path to the traits.md file for that persona."""
    return home(persona_id) / "traits.md"


def persona_trait(persona_id: str) -> Path:
    """Path to the persona-trait.md file for that persona."""
    return home(persona_id) / "persona-trait.md"


def struggles(persona_id: str) -> Path:
    """Path to the struggles.md file for that persona."""
    return home(persona_id) / "struggles.md"


def wishes(persona_id: str) -> Path:
    """Path to the wishes.md file for that persona."""
    return home(persona_id) / "wishes.md"


def permissions(persona_id: str) -> Path:
    """Path to the permissions.md file for that persona."""
    return home(persona_id) / "permissions.md"


def channels(persona_id: str) -> Path:
    """Path to the channels.md file for that persona."""
    return home(persona_id) / "channels.md"


def destiny(persona_id: str) -> Path:
    """Path to the destiny directory for that persona."""
    return home(persona_id) / "destiny"


def history(persona_id: str) -> Path:
    """Path to the history directory for that persona."""
    return home(persona_id) / "history"


def history_briefing(persona_id: str) -> Path:
    """Path to the history briefing index for that persona."""
    return home(persona_id) / "history" / "briefing.md"


def memory(persona_id: str) -> Path:
    """Path to the memory.json file — the persona's persisted mind state."""
    return home(persona_id) / "memory.json"


def health_log(persona_id: str) -> Path:
    """Path to the health.jsonl file — one line per health_check tick."""
    return home(persona_id) / "health.jsonl"


def training_set(persona_id: str) -> Path:
    """Path to the training directory for that persona."""
    return home(persona_id) / "training"


def media(persona_id: str) -> Path:
    """Path to the media directory for that persona."""
    return home(persona_id) / "media"


def gallery(persona_id: str) -> Path:
    """Path to the gallery.jsonl file for that persona."""
    return media(persona_id) / "gallery.jsonl"


def screenshots(persona_id: str) -> Path:
    """Directory where screenshots the persona captures of her own screen are saved."""
    return media(persona_id) / "screenshots"


def notes(persona_id: str) -> Path:
    """Path to the notes.md file for that persona."""
    return home(persona_id) / "notes.md"


def lora_adapter(persona_id: str) -> Path:
    """Persistent LoRA adapter directory for a persona."""
    return eternego_home() / "fine_tune" / persona_id / "adapter"


def routines(persona_id: str) -> Path:
    """Path to the routines.json file for that persona."""
    return home(persona_id) / "routines.json"


def add_routine(persona_id: str, spec: str, time: str, recurrence: str) -> None:
    """Add a routine entry to the persona's routines file."""
    logger.info("Adding routine", {"persona_id": persona_id, "spec": spec, "time": time, "recurrence": recurrence})
    path = routines(persona_id)
    data = filesystem.read_json(path) if path.exists() else {"routines": []}
    entry = {"spec": spec, "time": time, "recurrence": recurrence}
    data["routines"].append(entry)
    filesystem.write_json(path, data)


def diary(persona_id: str) -> Path:
    """Path to the diary directory for that persona."""
    return eternego_home() / "diary" / persona_id


def create_directory(path: Path) -> None:
    logger.info("Create a directory", {"path": path.name})

    path.mkdir(parents=True, exist_ok=True)


def save_as_json(persona_id: str, path: Path, content) -> None:
    """Save json content to the given path."""
    logger.info("Saving file for persona", {"persona_id": persona_id, "filename": path.name})
    filesystem.write_json(path, objects.json(content))


def save_as_binary(path: Path, content: bytes) -> None:
    """Save binary content to a file."""
    logger.info("Saving binary file", {"path": str(path)})
    filesystem.write_bytes(path, content)


def save_as_string(path: Path, content: str) -> None:
    """Save string content to a file."""
    logger.info("Saving string file", {"path": str(path)})
    filesystem.write(path, content)


def init_git(path: Path) -> None:
    """Initialize a git repository in the given path."""
    logger.info("Initializing git repository", {"path": str(path)})
    filesystem.ensure_dir(path)
    git.init(path)


def write_as_string(path: Path, content: str) -> None:
    """Append string content to a file."""
    logger.info("Writing to file", {"path": str(path)})
    filesystem.write(path, content)

def append_as_string(path: Path, content: str) -> None:
    """Append string content to a file."""
    logger.info("Appending to file", {"path": str(path)})
    filesystem.append(path, content)


def append_line(path: Path, line: str) -> None:
    """Append a single line to a file."""
    logger.info("Appending line to file", {"path": str(path)})
    filesystem.append(path, line + "\n")


def append_jsonl(path: Path, obj: dict) -> None:
    """Append a JSON object as a single line to a JSONL file."""
    import json
    filesystem.append(path, json.dumps(obj) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file and return a list of parsed objects."""
    import json
    if not path.exists():
        return []
    text = read(path)
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]


def meanings(persona_id: str) -> Path:
    """Directory where persona-specific meanings (.md) are stored."""
    return home(persona_id) / "meanings"


def lessons(persona_id: str) -> Path:
    """Directory where the lessons frontier wrote for this persona live."""
    return home(persona_id) / "lessons"


def learned(persona_id: str) -> Path:
    """Map file linking lesson_id to the meaning name derived from it."""
    return home(persona_id) / "meanings" / "learned.json"


def commit_diary(persona_id: str, diary_path: Path) -> None:
    """Commit the diary entry to git."""
    logger.info("Committing diary entry to git", {"persona_id": persona_id, "diary_path": str(diary_path)})
    git.add(diary_path, "*")
    git.commit(diary_path, "Persona diary entry date: " + str(datetimes.iso_8601(datetimes.now())))


def delete_recursively(path: Path) -> None:
    """Delete a file or directory and all its contents."""
    logger.info("Deleting path recursively", {"path": str(path)})
    filesystem.delete_dir(path)


def encrypt(archive: bytes, key: bytes) -> bytes:
    """Encrypt the given archive using the given key."""
    logger.info("Encrypting archive")
    return crypto.encrypt(archive, key)


def decrypt(path: Path, key: bytes) -> bytes:
    """Decrypt the contents of a file using the given key."""
    logger.info("Decrypting file", {"path": str(path)})
    encrypted = filesystem.read_bytes(path)
    return crypto.decrypt(encrypted, key)


def unzip(persona_id: str, archive: bytes) -> Path:
    """Unzip the given archive into a staging directory for the persona."""
    logger.info("Unzipping archive for persona", {"persona_id": persona_id})
    staging = eternego_home() / "temp" / persona_id
    filesystem.ensure_dir(staging)
    filesystem.unzip(archive, staging)
    return staging


def copy_recursively(source: Path, destination: Path) -> None:
    """Copy a file or directory and all its contents to the destination."""
    logger.info("Copying path recursively", {"source": str(source), "destination": str(destination)})
    filesystem.copy_dir(source, destination)


def read(path: Path) -> str:
    """Read text content from a file."""
    logger.info("Reading file", {"path": str(path)})
    if not path.exists():
        logger.warning("File not found", {"path": str(path)})
        return ""
    return filesystem.read(path).strip()


def read_json(path: Path) -> dict | None:
    """Read JSON content from a file."""
    logger.info("Reading JSON file", {"path": str(path)})
    if not path.exists():
        logger.warning("File not found", {"path": str(path)})
        return None
    return filesystem.read_json(path)


def md_dict(path: Path) -> dict[str, str]:
    """Parse a markdown file by `# ` headers; returns {header: body} per section.

    Lines before the first `# ` header are dropped. Empty file or missing file
    returns an empty dict.
    """
    if not path.exists():
        return {}
    sections: dict[str, str] = {}
    current_header: str | None = None
    current_body: list[str] = []
    for line in filesystem.read(path).splitlines():
        if line.startswith("# "):
            if current_header is not None:
                sections[current_header] = "\n".join(current_body).strip()
            current_header = line[2:].strip()
            current_body = []
        elif current_header is not None:
            current_body.append(line)
    if current_header is not None:
        sections[current_header] = "\n".join(current_body).strip()
    return sections


def md_list(path: Path, section: str) -> list[str]:
    """Return non-empty lines under a markdown section header (## section) from a file."""
    if not path.exists():
        return []
    inside = False
    result = []
    for line in filesystem.read(path).splitlines():
        if line.strip().lstrip("#").strip().lower() == section.lower():
            inside = True
            continue
        if inside:
            if line.startswith("#"):
                break
            if line.strip():
                result.append(line.strip())
    return result


def lines(path: Path) -> list[str]:
    """Read a file and return its non-empty lines as a list."""
    logger.info("Reading list from file", {"path": str(path)})
    if not path.exists():
        logger.warning("File not found", {"path": str(path)})
        return []
    content = filesystem.read(path)
    return [line for line in content.splitlines() if line.strip()]


def delete_entry(path: Path, hash_part: str) -> None:
    """Delete an entry from a file by its content hash."""
    logger.info("Deleting entry from file", {"path": str(path), "hash": hash_part})
    if not path.exists():
        logger.warning("File not found", {"path": str(path)})
        return
    content = filesystem.read(path)
    entry_lines = content.splitlines()
    remaining = [line for line in entry_lines if crypto.generate_unique_id(line) != hash_part]
    if len(remaining) == len(entry_lines):
        logger.warning("Entry not found or already modified", {"path": str(path), "hash": hash_part})
        return
    filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")


def find_and_delete_file(path: Path, hash_part: str) -> None:
    """Delete a file in a directory by its name hash."""
    logger.info("Finding and deleting file", {"path": str(path), "hash": hash_part})
    if not path.exists():
        logger.warning("Directory not found", {"path": str(path)})
        return
    for file in path.glob("*"):
        if crypto.generate_unique_id(file.stem) == hash_part:
            filesystem.delete(file)
            return
    logger.warning("File not found or already removed", {"path": str(path), "hash": hash_part})


def md_files(directory: Path) -> list[Path]:
    """Return a list of markdown files in the given directory."""
    logger.info("Listing markdown files in directory", {"directory": str(directory)})
    if not directory.exists():
        logger.warning("Directory not found", {"directory": str(directory)})
        return []
    return sorted([file for file in directory.glob("*.md") if file.is_file()])


def zip_home(persona_id: str) -> bytes:
    """Zip the entire persona's home directory and return the archive as bytes."""
    logger.info("Zipping persona's home directory", {"persona_id": persona_id})
    path = home(persona_id)
    if not path.exists():
        logger.error("Persona home directory not found", {"persona_id": persona_id})
        raise FileNotFoundError(f"Persona home directory not found for persona_id: {persona_id}")
    return filesystem.zip(path)


def add_training_set(persona_id: str, training_set_content: str) -> None:
    """Write the given training set content to a new file in the persona's training directory."""
    logger.info("Adding training set", {"persona_id": persona_id})
    training_dir = training_set(persona_id)
    if not training_dir.exists():
        training_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetimes.date_stamp(datetimes.now())
    filename = f"batch-{timestamp}.json"
    filesystem.write(training_dir / filename, training_set_content)


def add_history_entry(persona_id: str, event: str, content: str) -> str:
    """Write the given content to a new file in the persona's history directory.

    Returns the filename (relative to the history directory).
    """
    logger.info("Adding history entry", {"persona_id": persona_id})
    history_dir = history(persona_id)
    if not history_dir.exists():
        history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetimes.date_stamp(datetimes.now())
    filename = f"{event}-{timestamp}.md"
    filesystem.write(history_dir / filename, content)
    return filename


def save_destiny_entry(persona_id: str, event: str, trigger: str, content: str) -> None:
    """Write a destiny entry file named by event type and trigger datetime."""
    from datetime import datetime
    logger.info("Saving destiny entry", {"persona_id": persona_id, "event": event, "trigger": trigger})
    dt = datetime.strptime(trigger, "%Y-%m-%d %H:%M")
    created = datetimes.stamp(datetimes.now())
    filesystem.write(
        destiny(persona_id) / f"{event}-{dt.strftime('%Y-%m-%d-%H-%M')}-{created}.md",
        content,
    )


def destinies_in(persona_id: str, date_str: str) -> list[str]:
    """Return formatted scheduled events for a date (YYYY-MM-DD) or month (YYYY-MM).

    Projects recurring entries forward across the requested range, so a daily
    task scheduled with a single next-file still shows on every day of a week
    query, each flagged with its recurrence.
    """
    import calendar as _cal
    import re
    from datetime import datetime, timedelta
    logger.info("Reading scheduled events", {"persona_id": persona_id, "date": date_str})
    dest = destiny(persona_id)
    if not dest.exists():
        return []

    parts = date_str.split("-")
    try:
        if len(parts) == 3:
            start = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            end = start + timedelta(days=1)
        elif len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            start = datetime(y, m, 1)
            end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
        else:
            return []
    except (ValueError, IndexError):
        return []

    trigger_re = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})")
    events = []

    for f in sorted(dest.glob("*.md")):
        match = trigger_re.search(f.stem)
        if not match:
            continue
        try:
            trigger = datetime(
                int(match.group(1)), int(match.group(2)), int(match.group(3)),
                int(match.group(4)), int(match.group(5)),
            )
        except (ValueError, IndexError):
            continue
        content = read(f)
        if not content:
            continue

        recurrence = None
        body_lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("recurrence:"):
                recurrence = stripped.split(":", 1)[1].strip().lower() or None
            else:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()

        if start <= trigger < end:
            events.append((trigger, body, recurrence))

        if recurrence in ("hourly", "daily", "weekly"):
            step = {"hourly": timedelta(hours=1), "daily": timedelta(days=1), "weekly": timedelta(weeks=1)}[recurrence]
            nxt = trigger + step
            while nxt < end:
                if nxt >= start:
                    events.append((nxt, body, recurrence))
                nxt += step
        elif recurrence == "monthly":
            nxt = trigger
            while True:
                y, mo = (nxt.year + 1, 1) if nxt.month == 12 else (nxt.year, nxt.month + 1)
                day = min(trigger.day, _cal.monthrange(y, mo)[1])
                nxt = datetime(y, mo, day, trigger.hour, trigger.minute)
                if nxt >= end:
                    break
                if nxt >= start:
                    events.append((nxt, body, recurrence))

    events.sort(key=lambda e: e[0])
    return [
        f"- {t.strftime('%Y-%m-%d %H:%M')} — {b}" + (f" [recurring: {r}]" if r else "")
        for t, b, r in events
    ]


def due_destiny_entries(persona_id: str, before: "datetime") -> list[tuple[Path, str]]:
    """Return (filepath, content) for destiny entries with trigger time <= before (local)."""
    import re
    from datetime import datetime as dt_class
    logger.info("Reading due destiny entries", {"persona_id": persona_id})
    dest = destiny(persona_id)
    if not dest.exists():
        return []
    results = []
    pattern = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})")
    for f in sorted(dest.glob("*.md")):
        match = pattern.search(f.stem)
        if not match:
            continue
        try:
            trigger = dt_class(
                int(match.group(1)), int(match.group(2)), int(match.group(3)),
                int(match.group(4)), int(match.group(5)),
            )
            if trigger <= before.replace(tzinfo=None):
                content = read(f)
                if content:
                    results.append((f, content))
        except (ValueError, IndexError):
            continue
    return results


def read_files_matching(persona_id: str, directory: Path, pattern: str) -> list[str]:
    """Return 'File: name\\ncontent' entries for all non-empty files matching the glob pattern."""
    logger.info("Reading files matching pattern", {"persona_id": persona_id, "pattern": pattern})
    if not directory.exists():
        return []
    return [f"File: {f.name}\n{c}" for f in sorted(directory.glob(pattern)) if (c := read(f))]


def clear(path: Path) -> None:
    """Clear the contents of a file."""
    logger.info("Clearing file contents", {"path": str(path)})
    if path.exists():
        filesystem.write(path, "")
