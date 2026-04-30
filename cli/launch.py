"""CLI launch — start the daemon and open the dashboard in the user's browser."""

import asyncio
import threading
import time
import webbrowser

from application.platform import OS
from daemon import run as daemon_run


async def run(config):
    requested_port = config.port
    config.port = OS.find_free_port(config.host, config.port)
    if config.port != requested_port:
        print(f"Port {requested_port} was in use; using {config.port} instead.")

    url = f"http://{config.host}:{config.port}"

    def open_after_ready():
        # Give the web server a moment to bind before launching the browser.
        # If the user already had a tab open, this just refreshes their context.
        time.sleep(2)
        webbrowser.open(url)

    threading.Thread(target=open_after_ready, daemon=True).start()
    await daemon_run(config)
