"""Environment — preparing and verifying the environment for a persona to grow."""

from application.core import bus, agents, system, local_inference_engine, paths, channels
from application.core.exceptions import UnsupportedOS, InstallationError, EngineConnectionError, ModelError, AgentError
from application.business.outcome import Outcome


async def ready() -> Outcome[dict]:
    """Ensure the inference engine is running and ready to serve requests."""
    await bus.propose("Ensuring engine readiness", {})

    try:
        await local_inference_engine.ensure_running()
        await bus.broadcast("Engine is ready", {})
        return Outcome(success=True, message="Engine is ready")

    except EngineConnectionError as e:
        await bus.broadcast("Engine readiness check failed", {"error": str(e)})
        return Outcome(success=False, message="Could not start the local inference engine. Please reinstall following the installation guide at https://eternego.ai")


async def prepare(model: str | None = None) -> Outcome[dict]:
    """It makes it easy to set up and prepare an environment for your persona to grow."""
    await bus.propose("Preparing environment", {"model": model})

    try:
        if not await system.is_installed("git"):
            await system.install("git")

        if not await system.is_installed("ollama"):
            await system.install("ollama")

        await local_inference_engine.ensure_running()

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

    except ModelError as e:
        await bus.broadcast("Environment preparation failed", {
            "reason": "model",
            "model": model,
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


async def pair(code: str) -> Outcome[dict]:
    """Claim a pairing code and mark the channel as verified for the persona."""
    await bus.propose("Pairing channel", {"code": code})

    try:
        persona, channel_type, channel_name = agents.take_code(code)

        channel = next((ch for ch in (persona.channels or []) if ch.type == channel_type), None)
        if not channel:
            await bus.broadcast("Pairing failed", {"code": code, "reason": "invalid_channel"})
            return Outcome(success=False, message="The channel associated with this pairing code could not be found.")

        if channel.verified_at:
            await bus.broadcast("Pairing failed", {"code": code, "reason": "already_verified"})
            return Outcome(success=False, message="This channel is already verified.")

        channels.verify(persona, channel, channel_name)

        await bus.broadcast("Channel paired", {"persona_id": persona.id, "channel": channel.name})
        return Outcome(success=True, message="Channel paired successfully", data={"persona_id": persona.id, "channel": channel.name})

    except AgentError as e:
        await bus.broadcast("Pairing failed", {"code": code, "reason": str(e)})
        return Outcome(success=False, message=str(e))


async def check_model(model: str) -> Outcome[dict]:
    """Pull the model if needed and verify it is available and running."""
    await bus.propose("Checking model", {"model": model})

    try:
        if await local_inference_engine.check(model):
            await bus.broadcast("Model is ready", {"model": model})
            return Outcome(success=True, message="Model is ready", data={"model": model})

        await bus.broadcast("Model check failed", {"model": model})
        return Outcome(success=False, message="Model is not available")

    except ModelError as e:
        await bus.broadcast("Model check failed", {
            "reason": "model",
            "model": model,
            "error": str(e),
        })
        return Outcome(success=False, message=str(e))

    except EngineConnectionError as e:
        await bus.broadcast("Model check failed", {
            "reason": "connection",
            "model": model,
            "error": str(e),
        })
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")
