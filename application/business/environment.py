"""Environment — preparing and verifying the environment for a persona to grow."""

from application.core import bus, system, local_inference_engine
from application.core.exceptions import UnsupportedOS, InstallationError, EngineConnectionError
from application.business.outcome import Outcome


async def prepare(model: str | None = None) -> Outcome[dict]:
    """It makes it easy to set up and prepare an environment for your persona to grow."""
    await bus.propose("Preparing environment", {"model": model})

    try:
        if not await system.is_installed("git"):
            await system.install("git")

        if not await local_inference_engine.is_installed():
            await local_inference_engine.install()

        if not model:
            model = await local_inference_engine.get_default_model()

        if not model:
            await bus.broadcast("Environment preparation failed", {"reason": "no_model"})
            return Outcome(success=False, message="No model available. Please provide a model name.")

        if not await local_inference_engine.check(model):
            await local_inference_engine.pull(model)

        outcome = await check_model(model)
        if not outcome.success:
            await bus.broadcast("Environment preparation failed", {"model": model})
            return Outcome(success=False, message="Environment preparation failed")

        await bus.broadcast("Environment ready", {"model": model})

        return Outcome(success=True, message="Environment is ready", data={"model": model})

    except UnsupportedOS as e:
        await bus.broadcast("Environment preparation failed", {
            "reason": "unsupported_os",
            "error": str(e),
        })
        return Outcome(success=False, message="Your operating system is not supported. Eternego requires Linux, macOS, or Windows.")

    except InstallationError as e:
        await bus.broadcast("Environment preparation failed", {
            "reason": "installation",
            "error": str(e),
        })
        return Outcome(success=False, message=str(e))

    except EngineConnectionError as e:
        await bus.broadcast("Environment preparation failed", {
            "reason": "connection",
            "model": model,
            "error": str(e),
        })
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")


async def check_model(model: str) -> Outcome[dict]:
    """Pull the model if needed and verify it is available and running."""
    await bus.propose("Checking model", {"model": model})

    try:
        if await local_inference_engine.check(model):
            await bus.broadcast("Model is ready", {"model": model})
            return Outcome(success=True, message="Model is ready", data={"model": model})

        await bus.broadcast("Model check failed", {"model": model})
        return Outcome(success=False, message="Model is not available")

    except EngineConnectionError as e:
        await bus.broadcast("Model check failed", {
            "reason": "connection",
            "model": model,
            "error": str(e),
        })
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")
