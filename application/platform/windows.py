"""Windows — Windows-specific shell operations and secure storage."""

import shutil

from application.platform.tool import tool


async def is_installed(program: str) -> bool:
    """Check if a program is installed on Windows."""
    return shutil.which(program) is not None


async def install(program: str) -> None:
    """Install a program on Windows via winget."""
    packages = {
        "ollama": "Ollama.Ollama",
        "git":    "Git.Git",
    }
    if program not in packages:
        raise NotImplementedError(f"Automatic install of '{program}' is not supported on Windows.")
    winget_id = packages[program]
    code, out = await execute_on_sub_process(
        f"winget install {winget_id} --silent --accept-package-agreements --accept-source-agreements"
    )
    if code != 0:
        raise RuntimeError(f"winget failed to install {program}: {out}")


@tool("Execute a shell command on the person's Windows system via PowerShell. Use for any OS operation, "
      "running code, installing packages, checking status, file operations. "
      "If multiple commands are needed, wrap them in one call (e.g. cmd1; cmd2).")
async def execute_on_sub_process(command: str) -> tuple[int, str]:
    """Execute a command on Windows via PowerShell and return (return_code, output)."""
    import asyncio

    process = await asyncio.create_subprocess_exec(
        "powershell", "-Command", command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    output = stdout.decode() if process.returncode == 0 else stderr.decode()
    return process.returncode, output.strip()


def ram_gb() -> float:
    """Total system RAM in GB via wmic."""
    import subprocess
    try:
        result = subprocess.run(
            ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory", "/value"],
            capture_output=True, text=True,
        )
        for line in result.stdout.splitlines():
            if "=" in line:
                return round(int(line.split("=")[1].strip()) / (1024 ** 3), 1)
    except (ValueError, OSError):
        pass
    return 0.0


def cpu_name() -> str:
    """CPU model name via wmic."""
    import subprocess
    try:
        result = subprocess.run(
            ["wmic", "cpu", "get", "name", "/value"],
            capture_output=True, text=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Name="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "Unknown"


def gpu_vram_gb() -> float | None:
    """GPU VRAM in GB via CUDA, or None if unavailable."""
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
    except Exception:
        pass
    return None


async def store_secret(key: str, value: str) -> None:
    """Store a secret in the Windows Credential Manager."""
    import win32crypt

    credential = {
        "Type": 1,  # CRED_TYPE_GENERIC
        "TargetName": f"eternego:{key}",
        "UserName": "eternego",
        "CredentialBlob": value,
        "Persist": 2,  # CRED_PERSIST_LOCAL_MACHINE
    }
    win32crypt.CredWrite(credential)


async def retrieve_secret(key: str) -> str:
    """Retrieve a secret from the Windows Credential Manager."""
    import win32crypt

    credential = win32crypt.CredRead(f"eternego:{key}", 1)
    return credential["CredentialBlob"].decode()
