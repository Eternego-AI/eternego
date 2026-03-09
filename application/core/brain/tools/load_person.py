"""Load person — load what is known about the person into context."""

from application.core.brain.data import Tool


class _LoadPerson(Tool):
    name = "load_person"
    requires_permission = False
    meaning_only = True
    instruction = (
        "Tool: load_person\n"
        "Load known facts and traits about the person.\n"
        "Params: {}"
    )

    def execution(self):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.debug("load_person: loading person data", {"persona_id": persona.id})
            identity = paths.read(paths.person_identity(persona.id))
            traits = paths.read(paths.person_traits(persona.id))
            parts = []
            if identity:
                parts.append(f"Facts:\n{identity}")
            if traits:
                parts.append(f"Traits:\n{traits}")
            if not parts:
                return "no person data known yet"
            return "\n\n".join(parts)
        return _run


tool = _LoadPerson()
