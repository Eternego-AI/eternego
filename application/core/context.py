""" context module  - how to manage the persona's context and what it means for the persona's identity and behavior. """
from application.core import paths
from application.core.data import Persona
from application.core.exceptions import ContextError
from application.platform import logger, lists


async def add(persona: Persona, context) -> None:
    """Add context items to the persona's context file."""
    logger.info("Adding context items", {"persona_id": persona.id})
    try:
        context_items = lists.as_list(context)
        if context_items:
            await paths.append_context(persona.id, "".join(context_items) + "\n")
    except OSError as e:
        logger.error("Failed to add context items", {"persona_id": persona.id, "error": str(e)})
        raise ContextError("Failed to add context items") from e