"""Local inference engine — installation, availability, and model management."""

import asyncio
import json

from application.platform import logger, ollama, lora
from application.core.exceptions import EngineConnectionError


async def get_default_model() -> str | None:
    """Get the default model name from the running engine."""
    logger.info("Getting default model from local inference engine")
    try:
        data = await ollama.get("/api/tags")
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
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def register(model_name: str, base_model: str) -> None:
    """Register a named model in Ollama pointing at base_model, with no adapter.

    Creates a Modelfile reference — no blob copy, no extra disk space.
    After the first sleep, fine_tune() overwrites it with FROM base + ADAPTER.
    """
    logger.info("Registering model", {"model_name": model_name, "base_model": base_model})
    try:
        await ollama.post("/api/create", {"model": model_name, "from": base_model, "stream": False})
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


async def fine_tune(hf_model_id: str, training_set: str, base_model: str, model_name: str, persona_id: str) -> None:
    """Fine-tune a model using LoRA and register the result as a new Ollama model.

    Trains on the HuggingFace model (HF cache handles re-use across nights).
    Saves only the LoRA adapter (~100–300 MB) — no merge, no memory spike.
    Converts the adapter to GGUF and registers it with Ollama as:
      FROM <base_model>
      ADAPTER <adapter.gguf>
    The model_name is the existing persona model name — updated in place each night.
    """
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
    except (RuntimeError, OSError, TypeError, ValueError) as e:
        raise EngineConnectionError(f"Fine-tuning failed: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    finally:
        Path(output_gguf).unlink(missing_ok=True)


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
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
