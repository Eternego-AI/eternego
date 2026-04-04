"""Processes — async task scheduling and process isolation."""

import asyncio
import inspect
import os
import subprocess
import sys
import textwrap
from collections.abc import Callable


def run_async(closure: Callable) -> None:
    """Schedule a closure to run as a background async task."""
    asyncio.create_task(closure())


def on_separate_process(fn: Callable) -> tuple[int, str]:
    """Run a function in a separate process. Returns (exit_code, error_message).

    For nested/closure functions: extracts source and runs it standalone.
    For module-level functions: imports from the module.
    """
    module = inspect.getmodule(fn)
    name = fn.__name__

    # Nested function (defined inside another function) — extract source
    if fn.__qualname__ != fn.__name__:
        source = textwrap.dedent(inspect.getsource(fn))
        code = (
            f"import sys; sys.path.insert(0, {os.getcwd()!r})\n"
            f"{source}\n"
            f"{name}()\n"
        )
    else:
        # Top-level function — import from module
        code = (
            f"import sys; sys.path.insert(0, {os.getcwd()!r})\n"
            f"from {module.__name__} import {name}\n"
            f"{name}()\n"
        )

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
    )

    return result.returncode, result.stderr.strip()


async def on_separate_process_async(fn: Callable) -> tuple[int, str]:
    """Async version — runs on_separate_process without blocking the event loop."""
    return await asyncio.to_thread(on_separate_process, fn)
