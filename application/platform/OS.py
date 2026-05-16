"""OS — system-agnostic operating system operations."""

import asyncio
import json
import platform
import shutil
import socket

from application.platform import logger
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


def find_free_port(host: str, start: int, attempts: int = 20) -> int:
    """First port in [start, start+attempts) that we can bind on `host`."""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port in {start}..{start + attempts - 1} on {host}")


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
            code, out = await execute(
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
        code, out = await execute(
            f"winget install {packages[program]} --silent --accept-package-agreements --accept-source-agreements"
        )
        if code != 0:
            raise RuntimeError(f"winget failed to install {program}: {out}")
        return

    raise NotImplementedError("Unsupported OS")


@tool("Take a screenshot of the screen or a specific region. "
      "Captures the full screen by default at the display's native resolution. "
      "Pass left, top, width, height to zoom into a specific area. "
      "path: where to save the image.")
async def screenshot(left: int = 0, top: int = 0, width: int = 0, height: int = 0, path: str = "") -> str:
    """Capture a screenshot and return the file path.

    One native API per OS — Linux goes through xdg-desktop-portal so the
    same call works on every compositor (X11, KDE, GNOME, sway, hyprland);
    macOS shells out to Apple's `screencapture` (TCC-gated, errors loudly
    when permission is missing); Windows uses Pillow's ImageGrab (Win32 GDI).
    """
    import os as _os
    import tempfile

    if not path:
        fd, path = tempfile.mkstemp(suffix=".png")
        _os.close(fd)

    region_requested = bool(left or top or width or height)
    target_os = get_supported()

    if target_os == "linux":
        import shutil
        import uuid
        from urllib.parse import unquote, urlparse

        from dbus_next import Variant
        from dbus_next.aio import MessageBus
        from dbus_next.constants import BusType
        from dbus_next.introspection import Node

        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        try:
            # Hand-built introspection. We avoid bus.introspect() because the portal
            # daemon exposes properties with dashes in their names (KDE's PowerProfile-
            # Monitor `power-saver-enabled`), which dbus-next rejects as spec-invalid.
            portal_node = Node.parse(
                '<node>'
                '<interface name="org.freedesktop.portal.Screenshot">'
                '<method name="Screenshot">'
                '<arg type="s" name="parent_window" direction="in"/>'
                '<arg type="a{sv}" name="options" direction="in"/>'
                '<arg type="o" name="handle" direction="out"/>'
                '</method>'
                '</interface>'
                '</node>'
            )
            portal_obj = bus.get_proxy_object(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                portal_node,
            )
            portal = portal_obj.get_interface("org.freedesktop.portal.Screenshot")

            sender = bus.unique_name.replace(".", "_").lstrip(":")
            token = "eternego_" + uuid.uuid4().hex[:8]
            request_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

            # The Request object is created lazily by the portal once Screenshot is
            # invoked, so we hand-build its (fixed) introspection rather than fetch it.
            request_node = Node.parse(
                '<node>'
                '<interface name="org.freedesktop.portal.Request">'
                '<method name="Close"/>'
                '<signal name="Response">'
                '<arg type="u" name="response"/>'
                '<arg type="a{sv}" name="results"/>'
                '</signal>'
                '</interface>'
                '</node>'
            )
            request_obj = bus.get_proxy_object(
                "org.freedesktop.portal.Desktop", request_path, request_node
            )
            request = request_obj.get_interface("org.freedesktop.portal.Request")

            done = asyncio.get_running_loop().create_future()

            def on_response(code: int, results: dict) -> None:
                if not done.done():
                    done.set_result((code, results))

            request.on_response(on_response)

            await portal.call_screenshot(
                "",
                {
                    "interactive": Variant("b", False),
                    "handle_token": Variant("s", token),
                },
            )

            code, results = await asyncio.wait_for(done, timeout=60.0)
            if code != 0:
                raise RuntimeError(
                    f"xdg-desktop-portal denied or cancelled the screenshot (response={code})"
                )

            src = unquote(urlparse(results["uri"].value).path)
            if region_requested:
                from PIL import Image
                with Image.open(src) as img:
                    img.crop((left, top, left + width, top + height)).save(path, "PNG")
            else:
                shutil.copy(src, path)
        finally:
            bus.disconnect()

    elif target_os == "mac":
        import subprocess

        cmd = ["screencapture", "-x"]
        if region_requested:
            cmd += ["-R", f"{left},{top},{width},{height}"]
        cmd.append(path)
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(
                "screencapture failed — usually means Screen Recording permission is "
                "missing or not honored for this binary (System Settings → Privacy & "
                f"Security → Screen Recording): {result.stderr.decode().strip()}"
            )

    elif target_os == "windows":
        from PIL import ImageGrab

        if region_requested:
            img = ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True)
        else:
            img = ImageGrab.grab(all_screens=True)
        img.save(path, "PNG")

    else:
        raise NotImplementedError(f"screenshot not supported on this OS")

    return f"Screenshot saved to {path}"


async def default_screen_size() -> tuple[int, int]:
    """Width and height of the default screen in the unit the cursor uses.

    Whatever `desktop.mouse_move` accepts on this OS is what this returns.
    On macOS that's points; on Linux/Windows it's pixels (logical pixels
    under DPI awareness on Windows).

    Linux: tries `xrandr` first — works under both X11 and XWayland, which
    most KDE Wayland sessions provide by default. Falls back to
    `kscreen-doctor -j` (KDE pure Wayland). Final fallback takes one
    screenshot via the existing portal path and reads its dimensions.

    macOS: Quartz `CGDisplayBounds(CGMainDisplayID())` — returns points,
    matching pynput's `Controller.position`. Native pixels (what
    `screencapture` produces) are 2× this on Retina; we deliberately don't
    return those.

    Windows: `GetSystemMetrics` via ctypes — returns logical pixels,
    matching pynput's `SetCursorPos`.
    """
    target_os = get_supported()

    if target_os == "linux":
        import re
        import shutil

        if shutil.which("xrandr"):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "xrandr", "-q",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                out, _ = await proc.communicate()
                m = re.search(rb"current\s+(\d+)\s*x\s*(\d+)", out)
                if m:
                    return int(m.group(1)), int(m.group(2))
            except Exception as e:
                logger.debug("xrandr probe failed", {"error": str(e)})

        if shutil.which("kscreen-doctor"):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "kscreen-doctor", "-j",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                out, _ = await proc.communicate()
                data = json.loads(out.decode())
                primary = next((o for o in data.get("outputs", []) if o.get("primary")), None)
                if primary is None:
                    primary = next((o for o in data.get("outputs", []) if o.get("enabled")), None)
                if primary:
                    sz = primary.get("currentModeSize", {})
                    if sz.get("width") and sz.get("height"):
                        return int(sz["width"]), int(sz["height"])
            except Exception as e:
                logger.debug("kscreen-doctor probe failed", {"error": str(e)})

        # Last resort: take a screenshot and measure it.
        import os as _os
        import tempfile
        from PIL import Image
        fd, tmp = tempfile.mkstemp(suffix=".png")
        _os.close(fd)
        try:
            await screenshot(path=tmp)
            with Image.open(tmp) as img:
                return img.width, img.height
        finally:
            try:
                _os.unlink(tmp)
            except OSError:
                pass

    if target_os == "mac":
        from Quartz import CGMainDisplayID, CGDisplayBounds
        bounds = CGDisplayBounds(CGMainDisplayID())
        return int(bounds.size.width), int(bounds.size.height)

    if target_os == "windows":
        import ctypes
        u = ctypes.windll.user32
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1)

    raise NotImplementedError("default_screen_size not supported on this OS")


@tool("Execute a command that completes on its own and return its output. "
      "Use for commands with a natural end: reading files, checking system state, "
      "installing packages, running scripts, querying services. "
      "Do not use for programs that keep running — use run instead.")
async def execute(command: str) -> tuple[int, str]:
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


@tool("Start a program that keeps running. Use for GUI applications, services, or anything "
      "that should stay alive after this call returns. Output is not captured. "
      "Use execute afterward to check whether it is running or ready.")
async def run(command: str) -> tuple[int, str]:
    """Launch a detached process. Returns immediately once the process is started."""
    os = get_supported()

    if os == "linux" or os == "mac":
        await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        return 0, "Started"

    if os == "windows":
        await asyncio.create_subprocess_exec(
            "powershell", "-Command",
            f"Start-Process -FilePath cmd -ArgumentList '/c {command}' -WindowStyle Hidden",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return 0, "Started"

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
