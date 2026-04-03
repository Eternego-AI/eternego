"""Git — repository operations."""

import subprocess
from pathlib import Path

_QUIET = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}


def init(path: Path) -> None:
    """Initialize a git repository if not already initialized."""
    if not (path / ".git").exists():
        subprocess.run(["git", "init", "-b", "master", str(path)], check=True, **_QUIET)
        subprocess.run(["git", "config", "user.email", "persona@eternego.ai"], cwd=str(path), check=True, **_QUIET)
        subprocess.run(["git", "config", "user.name", "Eternego"], cwd=str(path), check=True, **_QUIET)


def add(path: Path, file: str) -> None:
    """Stage a file in the repository."""
    subprocess.run(["git", "add", file], cwd=str(path), check=True, **_QUIET)


def commit(path: Path, message: str) -> None:
    """Create a commit with the given message."""
    subprocess.run(["git", "commit", "-m", message], cwd=str(path), check=True, **_QUIET)
