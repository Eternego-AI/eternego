"""CLI uninstall command — remove the Eternego service and source code."""

import os
import platform
import shutil
import subprocess
from pathlib import Path

_OS = platform.system()
_INSTALL_DIR = Path.home() / ".eternego" / "source"
_PERSONA_DIR = Path.home() / ".eternego"


def run():
    print()
    print("This will:")
    print(f"  - Stop and remove the Eternego service")
    print(f"  - Remove the eternego CLI")
    print(f"  - Delete the installed code at {_INSTALL_DIR}")
    print()
    print("Your persona data at ~/.eternego will NOT be touched.")
    print()

    confirm = input("Continue? [y/N] ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    print()
    _stop_service()
    _remove_cli_link()
    _show_persona_message()
    _delete_source()


def _stop_service():
    print("Stopping and removing service...")
    if _OS == "Linux":
        subprocess.run(["systemctl", "--user", "stop", "eternego"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "--user", "disable", "eternego"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        service_file = Path.home() / ".config" / "systemd" / "user" / "eternego.service"
        service_file.unlink(missing_ok=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif _OS == "Darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/com.eternego"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        plist = Path.home() / "Library" / "LaunchAgents" / "com.eternego.plist"
        plist.unlink(missing_ok=True)
        log = Path.home() / "Library" / "Logs" / "eternego.log"
        log.unlink(missing_ok=True)

    elif _OS == "Windows":
        subprocess.run(
            ["powershell", "-Command",
             "Stop-ScheduledTask -TaskName Eternego -ErrorAction SilentlyContinue;"
             " Unregister-ScheduledTask -TaskName Eternego -Confirm:$false"
             " -ErrorAction SilentlyContinue"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def _remove_cli_link():
    print("Removing CLI...")
    if _OS == "Windows":
        venv_scripts = str(_INSTALL_DIR / ".venv" / "Scripts")
        subprocess.run(
            ["powershell", "-Command",
             f"$p = [Environment]::GetEnvironmentVariable('Path','User');"
             f" $new = ($p -split ';' | Where-Object {{ $_ -ne '{venv_scripts}' }}) -join ';';"
             f" [Environment]::SetEnvironmentVariable('Path', $new, 'User')"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        link = Path.home() / ".local" / "bin" / "eternego"
        link.unlink(missing_ok=True)


def _show_persona_message():
    print()
    print("Eternego has been uninstalled.")
    print()
    if _PERSONA_DIR.exists():
        print("Your persona data is preserved at:")
        print(f"  {_PERSONA_DIR}")
        print()
        if _OS == "Windows":
            print("To delete it permanently:")
            print(f"  Remove-Item -Recurse -Force {_PERSONA_DIR}")
        else:
            print("To delete it permanently:")
            print(f"  rm -rf {_PERSONA_DIR}")


def _delete_source():
    if not _INSTALL_DIR.exists():
        return
    # Move out of the install dir before deleting — required on Windows (and
    # avoids "directory busy" errors on some Linux filesystems too).
    os.chdir(str(Path.home()))
    if _OS == "Windows":
        # On Windows the running eternego.exe locks files in .venv, so schedule
        # a delayed cleanup via cmd /c that waits for the process to exit.
        cmd = f'ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{_INSTALL_DIR}"'
        subprocess.Popen(
            f'cmd /c "{cmd}"',
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            shutil.rmtree(_INSTALL_DIR)
        except OSError:
            print()
            print(f"Could not fully remove {_INSTALL_DIR}")
            print(f"Delete it manually: rm -rf '{_INSTALL_DIR}'")
