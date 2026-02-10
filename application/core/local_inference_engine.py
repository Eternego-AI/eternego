"""Local inference engine — installation, availability, and model management."""

from application.platform import logger, OS, linux, mac, windows, ollama
from application.core.exceptions import UnsupportedOS


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

    if platform == "linux":
        await linux.install(local_inference)
    elif platform == "mac":
        await mac.install(local_inference)
    elif platform == "windows":
        await windows.install(local_inference)


async def get_default_model() -> str | None:
    """Get the default model name from the running engine."""
    logger.info("Getting default model from local inference engine")
    data = ollama.get("/api/tags")
    models = data.get("models", [])
    if not models:
        return None
    return models[0]["name"]


async def pull(model: str) -> None:
    """Pull a model into the local inference engine."""
    logger.info("Pulling model", {"model": model})
    ollama.post("/api/pull", {"name": model, "stream": False})


async def check(model: str) -> bool:
    """Check if a model is pulled, available, and responding."""
    logger.info("Checking model availability", {"model": model})
    data = ollama.get("/api/tags")
    models = [m["name"] for m in data.get("models", [])]
    if model not in models:
        return False
    response = ollama.post("/api/generate", {"model": model, "prompt": "hi", "stream": False})
    return response.get("response") is not None
