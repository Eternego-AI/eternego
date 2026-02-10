"""System — generic program availability and installation."""

import subprocess

from application.platform import logger, OS, linux, mac, windows
from application.core.exceptions import UnsupportedOS, InstallationError


async def is_installed(program: str) -> bool:
    """Check if a program is installed on the current OS."""
    logger.info("Checking if program is installed", {"program": program})
    platform = OS.get_supported()

    if platform == "linux":
        return await linux.is_installed(program)
    if platform == "mac":
        return await mac.is_installed(program)
    if platform == "windows":
        return await windows.is_installed(program)

    raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")


async def install(program: str) -> None:
    """Install a program on the current OS."""
    logger.info("Installing program", {"program": program})
    platform = OS.get_supported()

    if platform is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")

    try:
        if platform == "linux":
            await linux.install(program)
        elif platform == "mac":
            await mac.install(program)
        elif platform == "windows":
            await windows.install(program)
    except (subprocess.CalledProcessError, NotImplementedError) as e:
        raise InstallationError(f"Failed to install {program}") from e
