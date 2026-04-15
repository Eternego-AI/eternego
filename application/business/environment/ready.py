"""Environment — ensuring the inference engine is running and ready."""

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine
from application.core.exceptions import EngineConnectionError


async def ready() -> Outcome[None]:
    """Ensure the inference engine is running and ready to serve requests."""
    await bus.propose("Ensuring engine readiness", {})

    try:
        await local_inference_engine.ensure_running()
        await bus.broadcast("Engine is ready", {})
        return Outcome(success=True, message="Engine is ready")

    except EngineConnectionError as e:
        await bus.broadcast("Engine readiness check failed", {"error": str(e)})
        return Outcome(
            success=False,
            message="""Could not start the local inference engine. 
            Please reinstall following the installation guide at https://eternego.ai""",
        )
