"""Paths — application directory layout."""

from pathlib import Path

from application.platform import filesystem, logger, objects, git, crypto, datetimes


async def eternego_home() -> Path:
    """Root directory for all Eternego data."""
    logger.info("Accessing Eternego home directory")
    return Path.home() / ".eternego"


async def personas_home() -> Path:
    """Root directory for all persona storage."""
    logger.info("Accessing personas home directory")
    return Path.home() / ".eternego" / "personas"


async def home(persona_id: str) -> Path:
    """Root directory for a specific persona."""
    logger.info("Accessing persona's home directory", {"persona_id": persona_id})
    return await personas_home() / persona_id


async def persona_identity(persona_id: str) -> Path:
    """Path to the config.json file for that persona."""
    logger.info("Accessing persona identity file", {"persona_id": persona_id})
    return await home(persona_id) / "config.json"


async def person_identity(persona_id: str) -> Path:
    """Path to the person.md file for that persona."""
    logger.info("Accessing person identity file", {"persona_id": persona_id})
    return await home(persona_id) / "person.md"


async def person_traits(persona_id: str) -> Path:
    """Path to the traits.md file for that persona."""
    logger.info("Accessing person traits file", {"persona_id": persona_id})
    return await home(persona_id) / "traits.md"


async def context(persona_id: str) -> Path:
    """Path to the persona-context.md file for that persona."""
    logger.info("Accessing persona context file", {"persona_id": persona_id})
    return await home(persona_id) / "context.md"


async def struggles(persona_id: str) -> Path:
    """Path to the struggles.md file for that persona."""
    logger.info("Accessing person's struggles file", {"persona_id": persona_id})
    return await home(persona_id) / "struggles.md"


async def memory(persona_id: str) -> Path:
    """Path to the memory.json file for that persona."""
    logger.info("Accessing persona memory file", {"persona_id": persona_id})
    return await home(persona_id) / "memory.json"


async def channels(persona_id: str) -> Path:
    """Path to the channels.md file for that persona."""
    logger.info("Accessing persona channels file", {"persona_id": persona_id})
    return await home(persona_id) / "channels.md"


async def skills(persona_id: str) -> Path:
    """Path to the skills directory for that persona."""
    logger.info("Accessing persona skills directory", {"persona_id": persona_id})
    return await home(persona_id) / "skills"


async def destiny(persona_id: str) -> Path:
    """Path to the destiny directory for that persona."""
    logger.info("Accessing persona destiny directory", {"persona_id": persona_id})
    return await home(persona_id) / "destiny"


async def history(persona_id: str) -> Path:
    """Path to the history directory for that persona."""
    logger.info("Accessing persona history directory", {"persona_id": persona_id})
    return await home(persona_id) / "history"


async def history_briefing(persona_id: str) -> Path:
    """Path to the history briefing index for that persona."""
    logger.info("Accessing persona history briefing file", {"persona_id": persona_id})
    return await home(persona_id) / "history" / "briefing.md"


async def permissions(persona_id: str) -> Path:
    """Path to the permissions.md file for that persona."""
    logger.info("Accessing persona permissions file", {"persona_id": persona_id})
    return await home(persona_id) / "permissions.md"


async def training_set(persona_id: str) -> Path:
    """Path to the training directory for that persona."""
    logger.info("Accessing persona training directory", {"persona_id": persona_id})
    return await home(persona_id) / "training"


async def dna(persona_id: str) -> Path:
    """Path to the dna.md file for that persona."""
    logger.info("Accessing persona DNA file", {"persona_id": persona_id})
    return await home(persona_id) / "dna.md"

async def routines(persona_id: str) -> Path:
    """Path to the routines.json file for that persona."""
    logger.info("Accessing persona routines file", {"persona_id": persona_id})
    return await home(persona_id) / "routines.json"


async def add_routine(persona_id: str, spec: str, time: str, recurrence: str) -> None:
    """Add a routine entry to the persona's routines file."""
    logger.info("Adding routine", {"persona_id": persona_id, "spec": spec, "time": time, "recurrence": recurrence})
    path = await routines(persona_id)
    data = filesystem.read_json(path) if path.exists() else {"routines": []}
    data["routines"].append({"spec": spec, "time": time, "recurrence": recurrence})
    filesystem.write_json(path, data)


async def diary(persona_id: str) -> Path:
    """Path to the diary directory for that persona."""
    logger.info("Accessing persona diary directory", {"persona_id": persona_id})
    return await eternego_home() / "diary" / persona_id


async def create_home(persona_id: str) -> None:
    """Create the home directory for a persona."""
    logger.info("Creating home directory for persona", {"persona_id": persona_id})
    (await personas_home() / persona_id).mkdir(parents=True, exist_ok=True)


async def create_directories(persona_id: str, directories: list[str]) -> None:
    """Create the directory structure for a persona."""
    logger.info("Creating directories for persona", {"persona_id": persona_id})
    base = await home(persona_id)
    for subdir in directories:
        (base / subdir).mkdir(parents=True, exist_ok=True)

        
async def save_as_json(persona_id: str, filename: Path, content) -> None:
    """Save a json content in file to the persona's home directory."""
    logger.info("Saving file for persona", {"persona_id": persona_id, "filename": filename.name})
    path = await home(persona_id) / filename
    filesystem.write_json(path, objects.json(content))
    

async def save_as_binary(path: Path, content: bytes) -> None:
    """Save binary content to a file."""
    logger.info("Saving binary file", {"path": str(path)})
    filesystem.write_bytes(path, content)

async def save_as_string(path: Path, content: str) -> None:
    """Save string content to a file."""
    logger.info("Saving string file", {"path": str(path)})
    filesystem.write(path, content)


async def init_git(path: Path) -> None:
    """Initialize a git repository in the given path."""
    logger.info("Initializing git repository", {"path": str(path)})
    filesystem.ensure_dir(path)
    git.init(path)


async def append_as_string(path: Path, content: str) -> None:
    """Append string content to a file."""
    logger.info("Appending to file", {"path": str(path)})
    filesystem.append(path, content)


async def commit_diary(persona_id: str, diary_path: Path) -> None:
    """Commit the diary entry to git."""
    logger.info("Committing diary entry to git", {"persona_id": persona_id, "diary_path": str(diary_path)})
    git.add(diary_path, "*")
    git.commit(diary_path, "Persona diary entry date: " + str(datetimes.iso_8601(datetimes.now())))


async def delete_recursively(path: Path) -> None:
    """Delete a file or directory and all its contents."""
    logger.info("Deleting path recursively", {"path": str(path)})
    filesystem.delete_dir(path)


async def encrypt(archive: bytes, key: bytes) -> bytes:
    """Encrypt the given archive using the given key."""
    logger.info("Encrypting archive")
    return crypto.encrypt(archive, key)


async def decrypt(path: Path, key: bytes) -> bytes:
    """Decrypt the contents of a file using the given key."""
    logger.info("Decrypting file", {"path": str(path)})
    encrypted = filesystem.read_bytes(path)
    return crypto.decrypt(encrypted, key)


async def unzip(persona_id: str, archive: bytes) -> Path:
    """Unzip the given archive into a staging directory for the persona."""
    logger.info("Unzipping archive for persona", {"persona_id": persona_id})
    staging = await eternego_home() / "temp" / persona_id
    filesystem.ensure_dir(staging)
    filesystem.unzip(archive, staging)
    return staging


async def copy_recursively(source: Path, destination: Path) -> None:
    """Copy a file or directory and all its contents to the destination."""
    logger.info("Copying path recursively", {"source": str(source), "destination": str(destination)})
    filesystem.copy_dir(source, destination)


async def read(path: Path) -> str:
    """Read text content from a file."""
    logger.info("Reading file", {"path": str(path)})
    if not path.exists():
        logger.warning("File not found", {"path": str(path)})
        return ""
    return filesystem.read(path).strip()


async def read_json(path: Path) -> dict | None:
    """Read JSON content from a file."""
    logger.info("Reading JSON file", {"path": str(path)})
    if not path.exists():
        logger.warning("File not found", {"path": str(path)})
        return None
    return filesystem.read_json(path)

async def append_context(persona_id: str, content: str) -> None:
    """Append text content to the persona's context file."""
    logger.info("Appending to context file", {"persona_id": persona_id})
    path = await context(persona_id)
    filesystem.append(path, content)


async def add_person_identity(persona_id: str, content: str) -> None:
    """Write text content to the persona's person-identity.md file."""
    logger.info("Adding person identity", {"persona_id": persona_id})
    path = await person_identity(persona_id)
    filesystem.write(path, content)


async def add_person_traits(persona_id: str, content: str) -> None:
    """Write text content to the persona's person-traits.md file."""
    logger.info("Adding person traits", {"persona_id": persona_id})
    path = await person_traits(persona_id)
    filesystem.write(path, content)


async def add_struggles(persona_id: str, content: str) -> None:
    """Write text content to the persona's person-struggles.md file."""
    logger.info("Adding struggles", {"persona_id": persona_id})
    path = await struggles(persona_id)
    filesystem.write(path, content)


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


async def lines(path: Path) -> list[str]:
    """Read a file and return its non-empty lines as a list."""
    logger.info("Reading list from file", {"path": str(path)})
    if not path.exists():
        logger.warning("File not found", {"path": str(path)})
        return []
    content = filesystem.read(path)
    return [line for line in content.splitlines() if line.strip()]


async def delete_entry(path: Path, hash_part: str) -> None:
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


async def find_and_delete_file(path: Path, hash_part: str) -> None:
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


async def add_to_skills(persona_id: str, skill_path: Path) -> Path:
    """Copy a skill file to the persona's skills directory."""
    logger.info("Adding skill to persona", {"persona_id": persona_id, "skill_path": str(skill_path)})
    destination = await skills(persona_id) / skill_path.name
    if destination.exists():
        logger.warning("Skill already exists", {"persona_id": persona_id, "skill": skill_path.stem})
        return destination
    filesystem.copy_file(skill_path, destination)
    return destination


async def add_history_briefing(persona_id: str, header: str, row: str) -> None:
    """Append an entry to the persona's history briefing index."""
    logger.info("Adding entry to history briefing", {"persona_id": persona_id, "row": row})
    briefing_path = await history_briefing(persona_id)

    if not briefing_path.exists():
        await save_as_string(briefing_path, header + "\n|-------|---------|------|\n")

    await save_as_string(briefing_path, row + "\n")


async def md_files(directory: Path) -> list[Path]:
    """Return a list of markdown files in the given directory."""
    logger.info("Listing markdown files in directory", {"directory": str(directory)})
    if not directory.exists():
        logger.warning("Directory not found", {"directory": str(directory)})
        return []
    # TODO: Exclude hidden files and directories, and ensure we only return files (not subdirectories)
    return sorted([file for file in directory.glob("*.md") if file.is_file()])


async def zip_home(persona_id: str) -> bytes:
    """Zip the entire persona's home directory and return the archive as bytes."""
    logger.info("Zipping persona's home directory", {"persona_id": persona_id})
    path = await home(persona_id)
    if not path.exists():
        logger.error("Persona home directory not found", {"persona_id": persona_id})
        raise FileNotFoundError(f"Persona home directory not found for persona_id: {persona_id}")
    return filesystem.zip(path)


async def read_history_brief(persona_id: str, default: str) -> str:
    """Read the history briefing index for the persona."""
    logger.info("Reading history briefing index", {"persona_id": persona_id})
    path = await history_briefing(persona_id)
    if not path.exists():
        logger.warning("History briefing file not found", {"persona_id": persona_id})
        return default

    content = filesystem.read(path)
    return content.strip() if content.strip() else default


async def write_dna(persona_id: str, dna_content: str) -> None:
    """Write the given DNA content to the persona's dna.md file."""
    logger.info("Writing DNA content", {"persona_id": persona_id})
    path = await dna(persona_id)
    filesystem.write(path, dna_content)


async def add_training_set(persona_id:str, training_set_content: str) -> None:
    """Write the given training set content to a new file in the persona's training directory."""
    logger.info("Adding training set", {"persona_id": persona_id})
    training_dir = await training_set(persona_id)
    if not training_dir.exists():
        training_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetimes.date_stamp(datetimes.now())
    filename = f"batch-{timestamp}.json"
    path = training_dir / filename
    filesystem.write(path, training_set_content)


async def add_history_entry(persona_id: str, event: str, content: str) -> None:
    """Write the given content to a new file in the persona's history directory."""
    logger.info("Adding history entry", {"persona_id": persona_id})
    history_dir = await history(persona_id)
    if not history_dir.exists():
        history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetimes.date_stamp(datetimes.now())
    filename = f"{event}-{timestamp}.md"
    path = history_dir / filename
    filesystem.write(path, content)


async def save_destiny_entry(persona_id: str, event: str, trigger: str, thread_id: str, content: str) -> None:
    """Write a destiny entry file named by event type and trigger datetime."""
    from datetime import datetime
    logger.info("Saving destiny entry", {"persona_id": persona_id, "event": event, "trigger": trigger})
    dt = datetime.strptime(trigger, "%Y-%m-%d %H:%M")
    created = datetimes.stamp(datetimes.now())
    directory = await destiny(persona_id)
    filesystem.write(directory / f"{event}-{dt.strftime('%Y-%m-%d-%H-%M')}-{thread_id[:8]}-{created}.md", content)


async def read_files_matching(persona_id: str, directory: Path, pattern: str) -> list[str]:
    """Return 'File: name\\ncontent' entries for all non-empty files matching the glob pattern."""
    logger.info("Reading files matching pattern", {"persona_id": persona_id, "pattern": pattern})
    if not directory.exists():
        return []
    return [f"File: {f.name}\n{c}" for f in sorted(directory.glob(pattern)) if (c := await read(f))]


async def clear(path: Path) -> None:
    """Clear the contents of a file."""
    logger.info("Clearing file contents", {"path": str(path)})
    if path.exists():
        filesystem.write(path, "")