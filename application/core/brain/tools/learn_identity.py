"""Learn identity — record a new identifying fact about the person."""

from application.core.brain.data import Tool


class _LearnIdentity(Tool):
    name = "learn_identity"
    requires_permission = False
    meaning_only = True
    instruction = (
        "Tool: learn_identity\n"
        "Record an identifying fact about the person.\n"
        'Params: {"fact": "the fact to record"}'
    )

    def execution(self, fact=""):
        async def _run(persona):
            from application.core import paths
            from application.platform import logger
            logger.debug("learn_identity: recording fact", {"persona_id": persona.id, "fact": fact[:80]})
            if not fact:
                return "no fact provided"
            paths.append_as_string(paths.person_identity(persona.id), fact + "\n")
            return f"recorded: {fact}"
        return _run


tool = _LearnIdentity()
