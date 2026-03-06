"""OS — detect operating system and dispatch hardware queries to OS-specific modules."""

import platform


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


def _module():
    os = get_supported()
    if os == "linux":
        from application.platform import linux
        return linux
    if os == "mac":
        from application.platform import mac
        return mac
    if os == "windows":
        from application.platform import windows
        return windows
    return None


def ram_gb() -> float:
    """Total system RAM in GB."""
    m = _module()
    return m.ram_gb() if m else 0.0


def gpu_vram_gb() -> float | None:
    """GPU VRAM in GB, or None if no compatible GPU detected."""
    m = _module()
    return m.gpu_vram_gb() if m else None


def cpu_name() -> str:
    """CPU model name."""
    m = _module()
    return m.cpu_name() if m else "Unknown"


def os_name() -> str:
    """Operating system name and version."""
    return f"{platform.system()} {platform.release()}".strip()
