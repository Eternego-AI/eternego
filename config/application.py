"""Application config — core application settings."""

import os
import sys
from pathlib import Path
from datetime import datetime

import config  # ensures .env is loaded

_PROJECT_ROOT = Path(__file__).parent.parent

# Path to convert_hf_to_gguf.py from llama.cpp — downloaded by install.sh into tools/.
# Override with GGUF_CONVERT_SCRIPT env var if the script lives elsewhere.
GGUF_CONVERT_SCRIPT: str = os.environ.get(
    "GGUF_CONVERT_SCRIPT",
    str(_PROJECT_ROOT / "tools" / "convert_hf_to_gguf.py"),
)

# Path to convert_lora_to_gguf.py from llama.cpp — downloaded by install.sh into tools/.
LORA_CONVERT_SCRIPT: str = os.environ.get(
    "LORA_CONVERT_SCRIPT",
    str(_PROJECT_ROOT / "tools" / "convert_lora_to_gguf.py"),
)

# Log directory — daily log files live here.
# Bundle (.dmg/.exe/.AppImage) always logs to ~/.eternego/logs since the bundle
# is read-only and dev never runs there. Source installs honour .env's LOGS_DIR
# (the installer scripts set it to ~/.eternego/logs); a bare clone falls back
# to ./logs.
if getattr(sys, "frozen", False):
    LOGS_DIR: Path = Path.home() / ".eternego" / "logs"
else:
    LOGS_DIR: Path = Path(os.environ.get("LOGS_DIR") or str(_PROJECT_ROOT / "logs"))


def log_file() -> Path:
    """Today's application log file."""
    return LOGS_DIR / f"eternego-{datetime.now().strftime('%Y-%m-%d')}.log"


def signal_log_file() -> Path:
    """Today's signal log file."""
    return LOGS_DIR / f"eternego-signals-{datetime.now().strftime('%Y-%m-%d')}.log"


def persona_log_file(persona_id: str) -> Path:
    """Today's per-persona log file. Used in debug mode to split traffic per persona."""
    return LOGS_DIR / f"eternego-{persona_id}-{datetime.now().strftime('%Y-%m-%d')}.log"
