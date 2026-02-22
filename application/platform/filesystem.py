"""Filesystem — directory creation, file read/write, archiving."""

import io
import json
import shutil
import zipfile
from pathlib import Path


def leaf(path: Path) -> str:
    """Last component of the path."""
    return path.name


def ensure_dir(path: Path) -> None:
    """Create directory and parents if they don't exist."""
    path.mkdir(parents=True, exist_ok=True)


def write(path: Path, content: str) -> None:
    """Write text content to a file."""
    ensure_dir(path.parent)
    path.write_text(content)


def write_json(path: Path, data: object) -> None:
    """Write JSON data to a file."""
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2))


def write_bytes(path: Path, data: bytes) -> None:
    """Write binary data to a file."""
    ensure_dir(path.parent)
    path.write_bytes(data)


def zip(source: Path) -> bytes:
    """Zip a directory into bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in source.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(source))
    return buffer.getvalue()


def append(path: Path, content: str) -> None:
    """Append text content to a file."""
    ensure_dir(path.parent)
    with open(path, "a") as f:
        f.write(content)


def read(path: Path) -> str:
    """Read text content from a file."""
    return path.read_text()


def read_bytes(path: Path) -> bytes:
    """Read binary data from a file."""
    return path.read_bytes()


def read_json(path: Path) -> dict:
    """Read JSON data from a file."""
    return json.loads(path.read_text())


def unzip(data: bytes, destination: Path) -> None:
    """Extract a zip archive from bytes to a directory."""
    ensure_dir(destination)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(destination)


def move(source: Path, destination: Path) -> None:
    """Move a file to a new location."""
    ensure_dir(destination.parent)
    source.rename(destination)


def delete(path: Path) -> None:
    """Delete a file."""
    path.unlink()


def delete_dir(path: Path) -> None:
    """Delete a directory tree."""
    shutil.rmtree(path, ignore_errors=True)


def copy_dir(source: Path, destination: Path) -> None:
    """Copy a directory tree to a new location."""
    shutil.copytree(source, destination, dirs_exist_ok=True)

def copy_file(source: Path, destination: Path) -> None:
    """Copy a single file to a new location."""
    ensure_dir(destination.parent)
    shutil.copy2(source, destination)