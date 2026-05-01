"""Local inference engine — installation, availability, and model management."""

import asyncio
import json

from application.platform import logger, ollama, lora, OS
from application.core import bus
from application.core.exceptions import EngineConnectionError, ModelError


async def ensure_running() -> None:
    """Ensure the local inference engine is running, start it if needed."""
    logger.info("Ensuring local inference engine is running")
    if await ollama.is_serving():
        return

    logger.info("Local inference engine not responding, starting server")
    os = OS.get_supported()
    if os == "linux":
        await OS.execute("systemctl start ollama")
    elif os == "mac":
        await OS.run("ollama serve")
    elif os == "windows":
        await OS.execute("Start-Process ollama -ArgumentList 'serve' -WindowStyle Hidden")

    for _ in range(10):
        await asyncio.sleep(1)
        if await ollama.is_serving():
            logger.info("Local inference engine is now running")
            return

    raise EngineConnectionError("Could not start the local inference engine")


async def get_default_model(url: str) -> str | None:
    """Get the default model name from the running engine."""
    logger.info("Getting default model from local inference engine", {"url": url})
    try:
        data = await ollama.get(url, "/api/tags")
    except ollama.OllamaError as e:
        raise ModelError(f"Failed to list models: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    models = data.get("models", [])
    if not models:
        return None
    return models[0]["name"]


async def pull(url: str, model: str) -> None:
    """Pull a model into the local inference engine."""
    logger.info("Pulling model", {"url": url, "model": model})
    try:
        async for chunk in ollama.stream(url, "/api/pull", {"name": model}):
            bus.share("Model pull progress", {"model": model, "status": chunk.get("status", ""), "total": chunk.get("total"), "completed": chunk.get("completed")})
    except ollama.OllamaError as e:
        raise ModelError(f"Failed to pull model '{model}': {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def register(url: str, model_name: str, base_model: str) -> None:
    """Register a named model in Ollama pointing at base_model, with no adapter."""
    logger.info("Registering model", {"url": url, "model_name": model_name, "base_model": base_model})
    try:
        async for chunk in ollama.stream(url, "/api/create", {"model": model_name, "from": base_model}):
            bus.share("Model create progress", {"model": model_name, "status": chunk.get("status", "")})
    except ollama.OllamaError as e:
        raise ModelError(f"Failed to register model '{model_name}': {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def delete(url: str, model: str) -> bool:
    """Delete a model from the local inference engine. Returns True on success, False on failure."""
    logger.info("Deleting model", {"url": url, "model": model})
    try:
        await ollama.delete(url, "/api/delete", {"name": model})
        return True
    except Exception:
        return False


async def check(url: str, model: str) -> bool:
    """Check if a model is pulled, available, and responding."""
    logger.info("Checking model availability", {"url": url, "model": model})
    try:
        data = await ollama.get(url, "/api/tags")
        models = [m["name"] for m in data.get("models", [])]
        if model not in models:
            return False
        response = await ollama.post(url, "/api/generate", {"model": model, "prompt": "hi", "stream": False})
        return response.get("response") is not None
    except ollama.OllamaError as e:
        raise ModelError(f"Model '{model}' check failed: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def fine_tune(hf_model_id: str, training_set: str, url: str, base_model: str, model_name: str, persona_id: str) -> None:
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

    logger.info("Fine-tuning model", {"url": url, "model": base_model, "pairs": len(training_pairs)})
    try:
        await asyncio.to_thread(lora.train, hf_model_id, training_pairs, output_gguf, str(adapter_dir))
        await ollama.post(url, "/api/create", {
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
