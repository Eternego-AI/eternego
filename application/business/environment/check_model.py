"""Environment — verifying a model is available and responding."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine, models
from application.core.data import Model
from application.core.exceptions import EngineConnectionError, ModelError


@dataclass
class CheckModelData:
    model: Model


async def check_model(model: Model) -> Outcome[CheckModelData]:
    """Verify the model is available and responding."""
    bus.propose("Checking model", {"model": model})

    try:
        if models.is_local(model):
            if await local_inference_engine.check(model.url, model.name):
                bus.broadcast("Model is ready", {"model": model.name})
                return Outcome(
                    success=True, message="Model is ready", data=CheckModelData(model=model)
                )

            bus.broadcast("Model check failed", {"model": model.name})
            return Outcome(success=False, message="Model is not available")

        await models.chat(model, [], "hi")
        bus.broadcast("Model is ready", {"model": model.name, "provider": model.provider})
        return Outcome(
            success=True, message="Model is ready", data=CheckModelData(model=model)
        )

    except ModelError as e:
        bus.broadcast(
            "Model check failed",
            {"reason": "model", "model": model.name, "error": str(e)},
        )
        return Outcome(success=False, message=str(e))

    except EngineConnectionError as e:
        bus.broadcast(
            "Model check failed",
            {"reason": "connection", "model": model.name, "error": str(e)},
        )
        return Outcome(success=False, message=str(e))
