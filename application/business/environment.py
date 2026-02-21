"""Environment — preparing and verifying the environment for a persona to grow."""

from datetime import timedelta

from application.core import bus, channels, system, local_inference_engine
from application.core.exceptions import UnsupportedOS, InstallationError, EngineConnectionError, ChannelError
from application.business.outcome import Outcome
from application.platform import datetimes


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


async def pair(code: str) -> Outcome[dict]:
    """Claim a pairing code and mark the channel as verified for the persona."""
    await bus.propose("Pairing channel", {"code": code})

    codes = await system.get_pairing_codes()
    entry = codes.get(code.upper())

    if not entry:
        await bus.broadcast("Pairing failed", {"code": code, "reason": "invalid"})
        return Outcome(success=False, message="Pairing code is invalid or has expired.")

    persona = entry["persona"]
    channel = entry["channel"]
    created_at = entry["created_at"]

    if channels.is_verified(persona, channel):
        await bus.broadcast("Pairing failed", {"code": code, "reason": "already_verified"})
        return Outcome(success=False, message="This channel is already verified.")

    if datetimes.now() - created_at > timedelta(minutes=10):
        await bus.broadcast("Pairing failed", {"code": code, "reason": "expired"})
        return Outcome(success=False, message="Pairing code has expired. Ask the persona to send a new message to get a fresh code.")

    try:
        channel.verified_at = datetimes.iso_8601(datetimes.now())
        channels.save(persona, channel)
        await bus.broadcast("Channel paired", {"persona": persona, "channel": channel})
        return Outcome(success=True, message="Channel verified successfully.", data={"persona": persona, "channel": channel})
    except ChannelError:
        await bus.broadcast("Pairing failed", {"code": code, "reason": "save_failed"})
        return Outcome(success=False, message="Failed to save the verified channel. Please try again.")


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
