"""Environment — setting up and preparing an environment for a persona to grow."""

import config.inference as config
from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine, system, models
from application.core.data import Model
from application.core.exceptions import (
    EngineConnectionError,
    InstallationError,
    ModelError,
    UnsupportedOS,
)

from .check_model import check_model


@dataclass
class PrepareData:
    model: Model


async def prepare(
    url: str,
    model: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
) -> Outcome[PrepareData]:
    """It makes it easy to set up and prepare an environment for your persona to grow."""
    bus.propose("Preparing environment", {"model": model, "provider": provider})

    try:
        if provider and not model:
            bus.broadcast(
                "Environment preparation failed", {"reason": "no_model"}
            )
            return Outcome(
                success=False,
                message="A model name is required when using a remote provider.",
            )

        if not model:
            await local_inference_engine.ensure_running()
            model = await local_inference_engine.get_default_model(config.OLLAMA_BASE_URL)

        if not model:
            bus.broadcast(
                "Environment preparation failed", {"reason": "no_model"}
            )
            return Outcome(
                success=False,
                message="No model available. Please provide a model name.",
            )
        

        model_obj = Model(name=model, provider=provider, api_key=api_key, url=url)

        if not await system.is_installed("git"):
                await system.install("git")

        if models.is_local(model_obj):
            if not await system.is_installed("ollama"):
                await system.install("ollama")

            await local_inference_engine.ensure_running()

            if not await local_inference_engine.check(url, model):
                await local_inference_engine.pull(config.OLLAMA_BASE_URL, model)

        
        outcome = await check_model(model_obj)

        if not outcome.success:
            bus.broadcast("Environment preparation failed", {"model": model})
            return Outcome(success=False, message=f"Environment preparation failed: {outcome.message}")

        bus.broadcast("Environment ready", {"model": model, "provider": provider})

        return Outcome(
            success=True, message="Environment is ready", data=PrepareData(model=model_obj)
        )

    except UnsupportedOS as e:
        bus.broadcast(
            "Environment preparation failed",
            {
                "reason": "unsupported_os",
                "error": str(e),
            },
        )
        return Outcome(
            success=False,
            message="Your operating system is not supported. Eternego requires Linux, macOS, or Windows.",
        )

    except InstallationError as e:
        bus.broadcast(
            "Environment preparation failed",
            {
                "reason": "installation",
                "error": str(e),
            },
        )
        return Outcome(success=False, message=str(e))

    except ModelError as e:
        bus.broadcast(
            "Environment preparation failed",
            {
                "reason": "model",
                "model": model,
                "error": str(e),
            },
        )
        return Outcome(success=False, message=str(e))

    except EngineConnectionError as e:
        bus.broadcast(
            "Environment preparation failed",
            {
                "reason": "connection",
                "model": model,
                "error": str(e),
            },
        )
        return Outcome(
            success=False,
            message=f"Could not connect to the local inference engine. Please make sure it is running. ({e})",
        )
