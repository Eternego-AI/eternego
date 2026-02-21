"""Processes — async task scheduling."""

import asyncio
from collections.abc import Callable


def run_async(closure: Callable) -> None:
    """Schedule a closure to run as a background async task."""
    asyncio.create_task(closure())
