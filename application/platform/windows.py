"""Windows — Windows-specific shell operations and secure storage."""

import shutil


async def is_installed(program: str) -> bool:
    """Check if a program is installed on Windows."""
    return shutil.which(program) is not None


async def install(program: str) -> None:
    """Install a program on Windows."""
    if program == "ollama":
        raise NotImplementedError("Please install Ollama from ollama.com")
