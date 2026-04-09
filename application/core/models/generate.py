"""Models — send a prompt to a model and return text."""

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama
import config.inference as cfg

from .chat import chat
from .is_local import is_local


async def generate(model: Model, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to a model and return the response text.

    For local models, uses the ollama generate endpoint.
    For remote models, wraps the prompt in a chat message.
    """
    logger.debug("models.generate", {"model": model.name, "provider": model.provider})

    if is_local(model):
        try:
            body = {"model": model.name, "prompt": prompt, "stream": False}
            if json_mode:
                body["format"] = "json"
            response = await ollama.post(model.url, "/api/generate", body)
            return response["response"].strip()
        except ollama.OllamaError as e:
            raise ModelError(f"Model returned an error: {e}") from e
        except ConnectionError as e:
            raise EngineConnectionError("Could not connect to the local inference engine") from e
        except KeyError as e:
            raise EngineConnectionError("Model returned an invalid response") from e

    return await chat(model, [{"role": "user", "content": prompt}])
