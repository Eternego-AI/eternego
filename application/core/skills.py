"""Skills — skill generation and management."""

from application.platform import logger


def basic_skills() -> dict[str, str]:
    """Generate the basic skills a persona starts with."""
    logger.info("Generating basic skills")
    return {}
