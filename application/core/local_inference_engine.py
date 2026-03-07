"""Local inference engine — installation, availability, and model management."""

import asyncio
import json
import shutil

from application.platform import logger, ollama, lora, hugging_face
from application.core.exceptions import EngineConnectionError


def is_supported(base_model: str) -> bool:
    """Return True if base_model has a known HuggingFace ID and can be fine-tuned."""
    from application.platform import hugging_face
    return hugging_face.id_for(base_model) is not None


def models() -> list[dict]:
    """Return supported base models enriched with hardware compatibility metadata.

    Each entry includes:
      name            — Ollama model name (e.g. "qwen2.5:7b")
      params_b        — parameter count in billions, or None if unknown
      ram_required_gb — estimated RAM needed for CPU/MPS bf16 fine-tuning
      fits            — True if current hardware can run fine-tuning
    """
    import re
    from application.platform import hugging_face, OS

    ram = OS.ram_gb()
    vram = OS.gpu_vram_gb()

    result = []
    for name in hugging_face.ids():
        m = re.search(r":(\d+(?:\.\d+)?)b", name.lower())
        params_b = float(m.group(1)) if m else None

        if params_b is not None:
            # CPU/MPS bf16: 2 bytes/param + ~1.5 GB overhead
            ram_required = round(params_b * 2.0 + 1.5, 1)
            # CUDA 4-bit QLoRA: 0.5 bytes/param + ~1.5 GB overhead
            vram_required = round(params_b * 0.5 + 1.5, 1)
            fits = (vram >= vram_required) if vram is not None else (ram >= ram_required)
        else:
            ram_required = None
            fits = True  # unknown size — no warning

        result.append({"name": name, "params_b": params_b, "ram_required_gb": ram_required, "fits": fits})

    return result


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


async def fine_tune(base_model: str, training_set: str, model_name: str, persona_id: str) -> None:
    """Fine-tune a model using LoRA and register the result as a new Ollama model.

    Trains on the HuggingFace base model (HF cache handles re-use across nights).
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

    hf_model_id = hugging_face.id_for(base_model)
    if hf_model_id is None:
        raise EngineConnectionError(
            f"No HuggingFace model ID known for '{base_model}' — "
            "add it to platform/hugging_face.py to enable fine-tuning"
        )

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
