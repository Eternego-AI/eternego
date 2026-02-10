"""Git — repository operations."""

import subprocess
from pathlib import Path


def init(path: Path) -> None:
    """Initialize a git repository if not already initialized."""
    if not (path / ".git").exists():
        subprocess.run(["git", "init", str(path)], check=True)


def add(path: Path, file: str) -> None:
    """Stage a file in the repository."""
    subprocess.run(["git", "add", file], cwd=str(path), check=True)


def commit(path: Path, message: str) -> None:
    """Create a commit with the given message."""
    subprocess.run(["git", "commit", "-m", message], cwd=str(path), check=True)
