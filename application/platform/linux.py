"""Linux — Linux-specific shell operations and secure storage."""

import asyncio
import shutil
import subprocess

_INSTALL_CMD = {
    "debian":  ("sudo", "apt", "install", "-y"),
    "fedora":  ("sudo", "dnf", "install", "-y"),
    "arch":    ("sudo", "pacman", "-S", "--noconfirm"),
    "suse":    ("sudo", "zypper", "install", "-y"),
    "alpine":  ("sudo", "apk", "add"),
}


def distro() -> str | None:
    """Return the Linux distro family: 'debian', 'fedora', 'arch', 'suse', 'alpine', or None."""
    id_like = ""
    distro_id = ""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    distro_id = line.strip().split("=", 1)[1].strip('"')
                elif line.startswith("ID_LIKE="):
                    id_like = line.strip().split("=", 1)[1].strip('"')
    except FileNotFoundError:
        return None
    ids = f"{distro_id} {id_like}"
    for family in ("debian", "fedora", "arch", "suse", "alpine"):
        if family in ids:
            return family
    return None


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
        return

    family = distro()
    if family not in _INSTALL_CMD:
        raise NotImplementedError(f"Unsupported distro family: {family}")

    process = await asyncio.create_subprocess_exec(
        *_INSTALL_CMD[family], program,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.communicate()


async def execute_on_sub_process(command: str) -> tuple[int, str]:
    """Execute a shell command on Linux and return (return_code, output)."""
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    output = stdout.decode() if process.returncode == 0 else stderr.decode()
    return process.returncode, output.strip()


async def store_secret(key: str, value: str) -> None:
    """Store a secret in the Linux Secret Service via secret-tool CLI."""
    subprocess.run(
        ["secret-tool", "store", "--label", f"eternego:{key}",
         "application", "eternego", "key", key],
        input=value.encode(),
        check=True,
    )


async def retrieve_secret(key: str) -> str:
    """Retrieve a secret from the Linux Secret Service via secret-tool CLI."""
    result = subprocess.run(
        ["secret-tool", "lookup", "application", "eternego", "key", key],
        capture_output=True, text=True, check=True,
    )
    value = result.stdout.strip()
    if not value:
        raise KeyError(f"Secret not found: {key}")
    return value
