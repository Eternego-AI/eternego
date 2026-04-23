"""Filesystem — directory creation, file read/write, archiving."""

import base64
import io
import json
import shutil
import zipfile
from pathlib import Path

from application.platform.tool import tool


def leaf(path) -> str:
    """Last component of the path."""
    return Path(path).name


def ensure_dir(path) -> None:
    """Create directory and parents if they don't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


@tool("Write text content to a file. Creates parent directories if needed. Overwrites if the file exists.")
def write(path: str, content: str) -> str:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(content)
    return f"Written to {path}"


def write_json(path, data: object) -> None:
    """Write JSON data to a file."""
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(json.dumps(data, indent=2))


def write_bytes(path, data: bytes) -> None:
    """Write binary data to a file."""
    p = Path(path)
    ensure_dir(p.parent)
    p.write_bytes(data)


def zip(source) -> bytes:
    """Zip a directory into bytes."""
    source = Path(source)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in source.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(source))
    return buffer.getvalue()


@tool("Append text content to the end of a file. Creates the file if it does not exist.")
def append(path: str, content: str) -> str:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "a") as f:
        f.write(content)
    return f"Appended to {path}"


@tool("Read text content from a file.")
def read(path: str) -> str:
    return Path(path).read_text()


def read_bytes(path) -> bytes:
    """Read binary data from a file."""
    return Path(path).read_bytes()


def read_base64(path) -> str:
    """Read a file and return its contents as a base64-encoded string."""
    return base64.b64encode(Path(path).read_bytes()).decode()


def read_json(path) -> dict:
    """Read JSON data from a file."""
    return json.loads(Path(path).read_text())


def unzip(data: bytes, destination) -> None:
    """Extract a zip archive from bytes to a directory."""
    destination = Path(destination)
    ensure_dir(destination)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(destination)


def move(source, destination) -> None:
    """Move a file to a new location."""
    destination = Path(destination)
    ensure_dir(destination.parent)
    Path(source).rename(destination)


@tool("Delete a file.")
def delete(path: str) -> str:
    Path(path).unlink()
    return f"Deleted {path}"


@tool("Create a directory and any parent directories needed.")
def create_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return f"Created directory {path}"


@tool("Delete a directory and everything inside it.")
def delete_dir(path: str) -> str:
    shutil.rmtree(path, ignore_errors=True)
    return f"Deleted directory {path}"


@tool("Copy a directory and everything inside it to a new location.")
def copy_dir(source: str, destination: str) -> str:
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return f"Copied {source} to {destination}"


def copy_file(source, destination) -> None:
    """Copy a single file to a new location."""
    destination = Path(destination)
    ensure_dir(destination.parent)
    shutil.copy2(source, destination)
