"""Desktop launcher — bundle-only entry for macOS .app and Windows .exe.

Sits at the project root (alongside daemon.py) because it isn't a CLI
subcommand — index.py picks it implicitly when running from a frozen
bundle on darwin/win32. The dev / Linux .AppImage / Docker paths still
use cli/launch.py unchanged. Adds a menu-bar / system-tray icon while
the daemon runs in a worker thread:

  - Click the icon (or "Open Dashboard") → reopens the web UI in the browser,
    using the actually-bound port (port-scan may have shifted off 5000).
  - "Quit" → trigger graceful daemon shutdown and stop the tray.

Selected by index.py only when `sys.frozen` is set AND `sys.platform` is
darwin / win32, so importing pystray never happens on the dev / Linux paths.
"""

import asyncio
import sys
import threading
import time
import webbrowser
from pathlib import Path

import pystray
from PIL import Image

from application.platform import OS
from daemon import run as daemon_run, stop as daemon_stop


def _icon_image() -> Image.Image:
    """Load the tray icon from the bundle's assets/."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    path = base / "assets" / "eternego-icon.png"
    if path.exists():
        return Image.open(path)
    # Dev fallback if the PNG hasn't been generated — solid violet square so
    # the tray is at least visible.
    return Image.new("RGBA", (64, 64), (138, 92, 255, 255))


def run(config) -> None:
    """Resolve port, run daemon in a worker thread, run tray on the main thread."""
    requested_port = config.port
    config.port = OS.find_free_port(config.host, config.port)
    if config.port != requested_port:
        print(f"Port {requested_port} was in use; using {config.port} instead.")

    url = f"http://{config.host}:{config.port}"

    def daemon_target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(daemon_run(config))
        finally:
            loop.close()

    daemon_thread = threading.Thread(target=daemon_target, name="eternego-daemon", daemon=True)
    daemon_thread.start()

    def open_browser_when_ready() -> None:
        time.sleep(2)
        webbrowser.open(url)

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    def on_open(_icon, _item) -> None:
        webbrowser.open(url)

    def on_quit(icon, _item) -> None:
        daemon_stop()
        icon.stop()
        daemon_thread.join(timeout=8)

    icon = pystray.Icon(
        "Eternego",
        _icon_image(),
        title="Eternego",
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", on_open, default=True),
            pystray.MenuItem("Quit", on_quit),
        ),
    )
    icon.run()
