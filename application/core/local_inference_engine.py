"""Local inference engine — installation, availability, and model management."""

import json
import subprocess
import tempfile
from pathlib import Path
from urllib.error import URLError

from application.platform import logger, OS, linux, mac, windows, ollama, lora, filesystem
from application.core.exceptions import UnsupportedOS, InstallationError, EngineConnectionError


async def is_installed() -> bool:
    """Check if a local inference engine is installed."""
    logger.info("Checking if local inference engine is installed")
    local_inference = "ollama"
    platform = OS.get_supported()

    if platform == "linux":
        return await linux.is_installed(local_inference)
    if platform == "mac":
        return await mac.is_installed(local_inference)
    if platform == "windows":
        return await windows.is_installed(local_inference)

    raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")


async def install() -> None:
    """Install a local inference engine."""
    logger.info("Installing local inference engine")
    local_inference = "ollama"
    platform = OS.get_supported()

    if platform is None:
        raise UnsupportedOS("Eternego requires Linux, macOS, or Windows")

    try:
        if platform == "linux":
            await linux.install(local_inference)
        elif platform == "mac":
            await mac.install(local_inference)
        elif platform == "windows":
            await windows.install(local_inference)
    except (subprocess.CalledProcessError, NotImplementedError) as e:
        raise InstallationError(f"Failed to install {local_inference}") from e


async def get_default_model() -> str | None:
    """Get the default model name from the running engine."""
    logger.info("Getting default model from local inference engine")
    try:
        data = ollama.get("/api/tags")
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    models = data.get("models", [])
    if not models:
        return None
    return models[0]["name"]


async def pull(model: str) -> None:
    """Pull a model into the local inference engine."""
    logger.info("Pulling model", {"model": model})
    try:
        ollama.post("/api/pull", {"name": model, "stream": False})
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def copy(source: str, destination: str) -> None:
    """Copy a model under a new name in the local inference engine."""
    logger.info("Copying model", {"source": source, "destination": destination})
    try:
        ollama.post("/api/copy", {"source": source, "destination": destination})
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def delete(model: str) -> None:
    """Delete a model from the local inference engine."""
    logger.info("Deleting model", {"model": model})
    try:
        ollama.delete("/api/delete", {"name": model})
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def fine_tune(model: str, training_set: str, new_model: str) -> None:
    """Fine-tune a model using LoRA and create a new Ollama model."""
    try:
        parsed = json.loads(training_set)
        training_pairs = parsed.get("training_pairs", [])
        logger.info("Fine-tuning model", {"model": model, "new_model": new_model, "training_set": parsed})

        with tempfile.TemporaryDirectory() as tmp_dir:
            formatted = lora.format(training_pairs)
            formatted_path = f"{tmp_dir}/training.json"
            filesystem.write(Path(formatted_path), json.dumps(formatted))

            adapter_path = lora.train(model, formatted_path, f"{tmp_dir}/lora_output")

            modelfile_content = f"FROM {model}\nADAPTER {adapter_path}"

            ollama.post("/api/create", {
                "name": new_model,
                "modelfile": modelfile_content,
            })

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise EngineConnectionError("Training data is malformed") from e
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def check(model: str) -> bool:
    """Check if a model is pulled, available, and responding."""
    logger.info("Checking model availability", {"model": model})
    try:
        data = ollama.get("/api/tags")
        models = [m["name"] for m in data.get("models", [])]
        if model not in models:
            return False
        response = ollama.post("/api/generate", {"model": model, "prompt": "hi", "stream": False})
        return response.get("response") is not None
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
