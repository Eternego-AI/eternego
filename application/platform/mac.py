"""Mac — macOS-specific shell operations and secure storage."""

import asyncio
import shutil

from application.platform.tool import tool


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


@tool("Execute a shell command on the person's macOS system. Use for any OS operation, "
      "running code, installing packages, checking status, file operations. "
      "If multiple commands are needed, wrap them in one call (e.g. cmd1 && cmd2).")
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


def ram_gb() -> float:
    """Total system RAM in GB via sysctl."""
    import subprocess
    try:
        result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
        return round(int(result.stdout.strip()) / (1024 ** 3), 1)
    except (ValueError, OSError):
        return 0.0


def cpu_name() -> str:
    """CPU model name via sysctl."""
    import subprocess
    try:
        result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        return result.stdout.strip() or "Apple Silicon"
    except OSError:
        return "Unknown"


def gpu_vram_gb() -> float | None:
    """GPU VRAM in GB via CUDA, or None (Apple Silicon uses unified memory)."""
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
    except Exception:
        pass
    return None


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
