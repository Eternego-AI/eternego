"""Linux — Linux-specific shell operations and secure storage."""

import asyncio
import shutil


async def is_installed(program: str) -> bool:
    """Check if a program is installed on Linux."""
    return shutil.which(program) is not None


async def install(program: str) -> None:
    """Install a program on Linux."""
    if program == "ollama":
        process = await asyncio.create_subprocess_shell(
            "curl -fsSL https://ollama.com/install.sh | sh",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
