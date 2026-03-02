"""Local inference engine — installation, availability, and model management."""

import json
import os
import tempfile

from application.platform import logger, ollama, lora, hugging_face
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


async def copy(source: str, destination: str) -> None:
    """Copy a model under a new name in the local inference engine."""
    logger.info("Copying model", {"source": source, "destination": destination})
    try:
        await ollama.post("/api/copy", {"source": source, "destination": destination})
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


async def fine_tune(base_model: str, training_set: str, new_model: str) -> None:
    """Fine-tune a model using LoRA and register the result as a new Ollama model.

    Downloads the HuggingFace base weights, trains a LoRA adapter, merges it,
    converts to GGUF, and registers the new model with Ollama.
    """
    try:
        parsed = json.loads(training_set)
        training_pairs = parsed.get("training_pairs", [])
        logger.info("Fine-tuning model", {"model": base_model, "new_model": new_model, "pairs": len(training_pairs)})

        hf_model_id = hugging_face.id_for(base_model)
        if hf_model_id is None:
            raise EngineConnectionError(
                f"No HuggingFace model ID known for '{base_model}' — "
                "add it to platform/hugging_face.py to enable fine-tuning"
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_gguf = os.path.join(tmp_dir, "model.gguf")
            lora.train(hf_model_id, training_pairs, output_gguf)

            await ollama.post("/api/create", {
                "name": new_model,
                "modelfile": f"FROM {output_gguf}",
            })

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise EngineConnectionError("Training data is malformed") from e
    except ImportError as e:
        raise EngineConnectionError(f"Fine-tuning dependencies not installed: {e}") from e
    except RuntimeError as e:
        raise EngineConnectionError(str(e)) from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


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
