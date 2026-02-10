"""Mac — macOS-specific shell operations and secure storage."""

import asyncio
import shutil


async def is_installed(program: str) -> bool:
    """Check if a program is installed on macOS."""
    return shutil.which(program) is not None


async def install(program: str) -> None:
    """Install a program on macOS."""
    if program == "ollama":
        process = await asyncio.create_subprocess_exec(
            "brew", "install", "ollama",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
