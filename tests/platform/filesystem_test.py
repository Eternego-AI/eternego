"""Filesystem tools — relative paths must be rejected.

The persona's character prompt gives her absolute paths for home / workspace /
media. Tools take absolute paths only — a relative path means a model that
didn't read the convention, and silently resolving it against CWD is what
caused tweet logs and other persona files to leak into the daemon's working
directory.
"""

import tempfile
from pathlib import Path

from application.platform import filesystem


def test_write_rejects_relative_path():
    try:
        filesystem.write("workspace/foo.md", "hi")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "absolute" in str(e)


def test_append_rejects_relative_path():
    try:
        filesystem.append("notes.md", "hi")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "absolute" in str(e)


def test_read_rejects_relative_path():
    try:
        filesystem.read("workspace/foo.md")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "absolute" in str(e)


def test_delete_rejects_relative_path():
    try:
        filesystem.delete("workspace/foo.md")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "absolute" in str(e)


def test_create_dir_rejects_relative_path():
    try:
        filesystem.create_dir("workspace/research")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "absolute" in str(e)


def test_delete_dir_rejects_relative_path():
    try:
        filesystem.delete_dir("workspace/research")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "absolute" in str(e)


def test_copy_dir_rejects_relative_source():
    try:
        filesystem.copy_dir("workspace/a", "/tmp/b")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "source" in str(e) and "absolute" in str(e)


def test_copy_dir_rejects_relative_destination():
    try:
        filesystem.copy_dir("/tmp/a", "workspace/b")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "destination" in str(e) and "absolute" in str(e)


def test_write_accepts_absolute_path():
    with tempfile.TemporaryDirectory() as tmp:
        target = str(Path(tmp) / "foo.md")
        filesystem.write(target, "hello")
        assert Path(target).read_text() == "hello"


def test_append_accepts_absolute_path():
    with tempfile.TemporaryDirectory() as tmp:
        target = str(Path(tmp) / "log.md")
        filesystem.append(target, "line 1\n")
        filesystem.append(target, "line 2\n")
        assert Path(target).read_text() == "line 1\nline 2\n"
