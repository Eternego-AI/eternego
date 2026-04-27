"""OS — system-agnostic operating system operations."""

import asyncio
import platform
import shutil

from application.platform.tool import tool


_secret_cache: dict[str, str] = {}
_secret_cache_only: bool = False


def get_supported() -> str | None:
    """Return 'linux', 'mac', 'windows', or None if unsupported."""
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "mac"
    if system == "windows":
        return "windows"
    return None


def ram_gb() -> float:
    """Total system RAM in GB."""
    os = get_supported()

    if os == "linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return round(int(line.split()[1]) / (1024 * 1024), 1)
        except OSError:
            pass
        return 0.0

    if os == "mac":
        import subprocess
        try:
            result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            return round(int(result.stdout.strip()) / (1024 ** 3), 1)
        except (ValueError, OSError):
            return 0.0

    if os == "windows":
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

    return 0.0


def gpu_vram_gb() -> float | None:
    """GPU VRAM in GB, or None if no compatible GPU detected."""
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
    except Exception:
        pass
    return None


def cpu_name() -> str:
    """CPU model name."""
    os = get_supported()

    if os == "linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return "Unknown"

    if os == "mac":
        import subprocess
        try:
            result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
            return result.stdout.strip() or "Apple Silicon"
        except OSError:
            return "Unknown"

    if os == "windows":
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

    return "Unknown"


def os_name() -> str:
    """Operating system name and version."""
    return f"{platform.system()} {platform.release()}".strip()


async def is_installed(program: str) -> bool:
    """Check if a program is installed on the current OS."""
    return shutil.which(program) is not None


async def install(program: str) -> None:
    """Install a program on the current OS."""
    os = get_supported()

    if program == "ollama":
        if os == "linux":
            process = await asyncio.create_subprocess_shell(
                "curl -fsSL https://ollama.com/install.sh | sh",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return
        if os == "mac":
            process = await asyncio.create_subprocess_exec(
                "brew", "install", "ollama",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return
        if os == "windows":
            code, out = await execute_on_sub_process(
                "winget install Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements"
            )
            if code != 0:
                raise RuntimeError(f"winget failed to install ollama: {out}")
            return

    if os == "linux":
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
            raise NotImplementedError("Could not detect Linux distribution")
        ids = f"{distro_id} {id_like}"
        family = None
        for f in ("debian", "fedora", "arch", "suse", "alpine"):
            if f in ids:
                family = f
                break
        install_cmd = {
            "debian": ("sudo", "apt", "install", "-y"),
            "fedora": ("sudo", "dnf", "install", "-y"),
            "arch": ("sudo", "pacman", "-S", "--noconfirm"),
            "suse": ("sudo", "zypper", "install", "-y"),
            "alpine": ("sudo", "apk", "add"),
        }
        if family not in install_cmd:
            raise NotImplementedError(f"Unsupported distro family: {family}")
        process = await asyncio.create_subprocess_exec(
            *install_cmd[family], program,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        return

    if os == "mac":
        process = await asyncio.create_subprocess_exec(
            "brew", "install", program,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        return

    if os == "windows":
        packages = {"git": "Git.Git"}
        if program not in packages:
            raise NotImplementedError(f"Automatic install of '{program}' is not supported on Windows.")
        code, out = await execute_on_sub_process(
            f"winget install {packages[program]} --silent --accept-package-agreements --accept-source-agreements"
        )
        if code != 0:
            raise RuntimeError(f"winget failed to install {program}: {out}")
        return

    raise NotImplementedError("Unsupported OS")


@tool("Take a screenshot of the screen or a specific region. "
      "Captures the full screen by default. Pass left, top, width, height to zoom into a specific area. "
      "path: where to save the image.")
def screenshot(left: int = 0, top: int = 0, width: int = 0, height: int = 0, path: str = "") -> str:
    """Capture a screenshot and return the file path."""
    import mss
    import os
    import tempfile

    if not path:
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

    with mss.mss() as sct:
        if left == 0 and top == 0 and width == 0 and height == 0:
            region = sct.monitors[0]
        else:
            region = {"left": left, "top": top, "width": width, "height": height}
        img = sct.grab(region)
        mss.tools.to_png(img.rgb, img.size, output=path)

    return f"Screenshot saved to {path}"


@tool("Execute a shell command on the person's system. Use for any OS operation, "
      "running code, installing packages, checking status, file operations. "
      "If multiple commands are needed, wrap them in one call (e.g. cmd1 && cmd2).")
async def execute_on_sub_process(command: str) -> tuple[int, str]:
    """Execute a shell command and return (return_code, output)."""
    os = get_supported()

    if os == "linux" or os == "mac":
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = stdout.decode() if process.returncode == 0 else stderr.decode()
        return process.returncode, output.strip()

    if os == "windows":
        process = await asyncio.create_subprocess_exec(
            "powershell", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = stdout.decode() if process.returncode == 0 else stderr.decode()
        return process.returncode, output.strip()

    raise NotImplementedError("Unsupported OS")


async def store_secret(key: str, value: str) -> None:
    """Store a secret in the OS secure storage. Caches in memory."""
    _secret_cache[key] = value

    if _secret_cache_only:
        return

    os = get_supported()

    if os == "linux":
        import subprocess
        subprocess.run(
            ["secret-tool", "store", "--label", f"eternego:{key}",
             "application", "eternego", "key", key],
            input=value.encode(),
            check=True,
        )
        return

    if os == "mac":
        import subprocess
        subprocess.run([
            "security", "add-generic-password",
            "-a", "eternego",
            "-s", f"eternego:{key}",
            "-w", value,
            "-U",
        ], check=True)
        return

    if os == "windows":
        import win32cred
        credential = {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": f"eternego:{key}",
            "UserName": "eternego",
            "CredentialBlob": value,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        }
        win32cred.CredWrite(credential, 0)
        return


async def retrieve_secret(key: str) -> str:
    """Retrieve a secret from OS secure storage. Returns from cache if available."""
    if key in _secret_cache:
        return _secret_cache[key]

    if _secret_cache_only:
        raise KeyError(f"Secret not found: {key}")

    os = get_supported()

    if os == "linux":
        import subprocess
        result = subprocess.run(
            ["secret-tool", "lookup", "application", "eternego", "key", key],
            capture_output=True, text=True, check=True,
        )
        value = result.stdout.strip()
        if not value:
            raise KeyError(f"Secret not found: {key}")
        return value

    if os == "mac":
        import subprocess
        result = subprocess.run([
            "security", "find-generic-password",
            "-a", "eternego",
            "-s", f"eternego:{key}",
            "-w",
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()

    if os == "windows":
        import win32cred
        credential = win32cred.CredRead(f"eternego:{key}", win32cred.CRED_TYPE_GENERIC)
        return credential["CredentialBlob"].decode("utf-16-le").rstrip("\x00")

    raise KeyError(f"Secret not found: {key}")
