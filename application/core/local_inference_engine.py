"""Local inference engine — installation, availability, and model management."""

import asyncio
import json

from application.platform import logger, ollama, lora, OS, linux, mac, windows
from application.core.exceptions import EngineConnectionError, ModelError


async def ensure_running() -> None:
    """Ensure the local inference engine is running, start it if needed."""
    logger.info("Ensuring local inference engine is running")
    if await ollama.is_serving():
        return

    logger.info("Local inference engine not responding, starting server")
    platform = OS.get_supported()
    if platform == "linux":
        await linux.execute_on_sub_process("systemctl start ollama")
    elif platform == "mac":
        await mac.execute_on_sub_process("ollama serve >/dev/null 2>&1 &")
    elif platform == "windows":
        await windows.execute_on_sub_process("Start-Process ollama -ArgumentList 'serve' -WindowStyle Hidden")

    for _ in range(10):
        await asyncio.sleep(1)
        if await ollama.is_serving():
            logger.info("Local inference engine is now running")
            return

    raise EngineConnectionError("Could not start the local inference engine")


async def get_default_model() -> str | None:
    """Get the default model name from the running engine."""
    logger.info("Getting default model from local inference engine")
    try:
        data = await ollama.get("/api/tags")
    except ollama.OllamaError as e:
        raise ModelError(f"Failed to list models: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    models = data.get("models", [])
    if not models:
        return None
    return models[0]["name"]


async def pull(model: str) -> None:
    """Pull a model into the local inference engine."""
    logger.info("Pulling model", {"model": model})
    try:
        await ollama.post("/api/pull", {"name": model, "stream": False})
    except ollama.OllamaError as e:
        raise ModelError(f"Failed to pull model '{model}': {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def register(model_name: str, base_model: str) -> None:
    """Register a named model in Ollama pointing at base_model, with no adapter."""
    logger.info("Registering model", {"model_name": model_name, "base_model": base_model})
    try:
        await ollama.post("/api/create", {"model": model_name, "from": base_model, "stream": False})
    except ollama.OllamaError as e:
        raise ModelError(f"Failed to register model '{model_name}': {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def delete(model: str) -> bool:
    """Delete a model from the local inference engine. Returns True on success, False on failure."""
    logger.info("Deleting model", {"model": model})
    try:
        await ollama.delete("/api/delete", {"name": model})
        return True
    except Exception:
        return False


async def check(model: str) -> bool:
    """Check if a model is pulled, available, and responding."""
    logger.info("Checking model availability", {"model": model})
    try:
        data = await ollama.get("/api/tags")
        models = [m["name"] for m in data.get("models", [])]
        if model not in models:
            return False
        response = await ollama.post("/api/generate", {"model": model, "prompt": "hi", "stream": False})
        return response.get("response") is not None
    except ollama.OllamaError as e:
        raise ModelError(f"Model '{model}' check failed: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def fine_tune(hf_model_id: str, training_set: str, base_model: str, model_name: str, persona_id: str) -> None:
    """Fine-tune a model using LoRA and register the result as a new Ollama model."""
    try:
        parsed = json.loads(training_set)
        training_pairs = parsed.get("training_pairs", [])
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise EngineConnectionError("Training data is malformed") from e

    from application.core import paths
    from pathlib import Path

    adapter_dir = paths.lora_adapter(persona_id)
    fine_tune_dir = paths.eternego_home() / "fine_tune" / persona_id
    fine_tune_dir.mkdir(parents=True, exist_ok=True)
    output_gguf = str(fine_tune_dir / "adapter.gguf")

    logger.info("Fine-tuning model", {"model": base_model, "pairs": len(training_pairs)})
    try:
        await asyncio.to_thread(lora.train, hf_model_id, training_pairs, output_gguf, str(adapter_dir))
        await ollama.post("/api/create", {
            "model": model_name,
            "from": base_model,
            "adapters": {"path": output_gguf},
            "stream": False,
        })
    except ImportError as e:
        raise EngineConnectionError(f"Fine-tuning dependencies not installed: {e}") from e
    except ollama.OllamaError as e:
        raise ModelError(f"Failed to register fine-tuned model '{model_name}': {e}") from e
    except (RuntimeError, OSError, TypeError, ValueError) as e:
        raise EngineConnectionError(f"Fine-tuning failed: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    finally:
        Path(output_gguf).unlink(missing_ok=True)
