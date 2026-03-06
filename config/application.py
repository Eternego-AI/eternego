"""Application config — core application settings."""

import os
from pathlib import Path

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

# Log file paths — written by the service, tailed by the CLI.
LOG_FILE: str = os.environ.get("LOG_FILE", str(_PROJECT_ROOT / "eternego.log"))
SIGNAL_LOG_FILE: str = os.environ.get("SIGNAL_LOG_FILE", str(_PROJECT_ROOT / "eternego-signals.log"))
