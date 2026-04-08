"""Models — model locality check."""

from application.core.data import Model
from application.platform import logger


def is_local(model: Model) -> bool:
    """A model is local when it has no remote provider."""
    logger.info("models.is_local", {"model": model.name, "provider": model.provider})
    return model.provider is None
