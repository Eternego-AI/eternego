"""Run tests using the EternegoAI test-runner.

Downloads the latest release to system temp if not already cached.
Usage: python test.py [directory]
"""

import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


REPO = "Eternego-AI/test-runner"
TMP_DIR = Path(tempfile.gettempdir()) / "eternego-test-runner"


def os_name():
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


def download():
    print("Downloading test-runner...")
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    release = json.loads(
        urllib.request.urlopen(f"https://api.github.com/repos/{REPO}/releases/latest").read()
    )
    asset_name = f"test-runner-{os_name()}.zip"
    asset = next((a for a in release["assets"] if a["name"] == asset_name), None)
    if not asset:
        print(f"Error: Could not find {asset_name} in latest release.")
        sys.exit(1)

    data = urllib.request.urlopen(asset["browser_download_url"]).read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(TMP_DIR)
    print("Done.")


if __name__ == "__main__":
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "tests"

    if not (TMP_DIR / "test_runner").exists():
        download()

    project_dir = str(Path(__file__).parent)
    python = sys.executable

    sys.exit(subprocess.run(
        [python, "-m", "test_runner", test_dir],
        env={**os.environ, "PYTHONPATH": f"{TMP_DIR}{os.pathsep}{project_dir}"},
    ).returncode)
