"""Learn identity — record a new identifying fact about the person."""

from application.core.brain.data import Trait


class _LearnIdentity(Trait):
    name = "learn_identity"
    requires_permission = False
    description = (
        "Records a new identifying fact about the person — name, role, location, or any stable "
        "detail about who they are. Use when the person shares something fundamental about themselves."
    )
    instruction = (
        "Trait: learn_identity\n"
        "Record an identifying fact about the person.\n"
        'Params: {"fact": "the fact to record"}'
    )

    def execution(self, fact=""):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.info("learn_identity: recording fact", {"persona_id": persona.id})
            if not fact:
                return "no fact provided"
            paths.add_person_identity(persona.id, fact + "\n")
            return f"recorded: {fact}"
        return _run


trait = _LearnIdentity()
