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
    elif program == "git":
        process = await asyncio.create_subprocess_exec(
            "brew", "install", "git",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()


async def execute_on_sub_process(command: str) -> tuple[int, str]:
    """Execute a shell command on macOS and return (return_code, output)."""
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    output = stdout.decode() if process.returncode == 0 else stderr.decode()
    return process.returncode, output.strip()


async def store_secret(key: str, value: str) -> None:
    """Store a secret in the macOS Keychain."""
    import subprocess

    subprocess.run([
        "security", "add-generic-password",
        "-a", "eternego",
        "-s", f"eternego:{key}",
        "-w", value,
        "-U",
    ], check=True)


async def retrieve_secret(key: str) -> str:
    """Retrieve a secret from the macOS Keychain."""
    import subprocess

    result = subprocess.run([
        "security", "find-generic-password",
        "-a", "eternego",
        "-s", f"eternego:{key}",
        "-w",
    ], capture_output=True, text=True, check=True)
    return result.stdout.strip()
