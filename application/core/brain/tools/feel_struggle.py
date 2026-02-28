"""Feel struggle — record a struggle or recurring obstacle the person faces."""

from application.core.brain.data import Tool


class _FeelStruggle(Tool):
    name = "feel_struggle"
    requires_permission = False
    description = (
        "Records a struggle, recurring obstacle, or difficulty the person faces. "
        "Use when the person describes something they find hard, frustrating, or repeatedly problematic."
    )
    instruction = (
        "Tool: feel_struggle\n"
        "Record a struggle or recurring obstacle the person faces.\n"
        'Params: {"struggle": "the struggle to record"}'
    )

    def execution(self, struggle=""):
        async def _run(persona):
            from application.core import paths, prompts, local_model
            from application.platform import logger, processes
            logger.debug("feel_struggle: recording struggle", {"persona_id": persona.id, "struggle": struggle[:80]})
            if not struggle:
                return "no struggle provided"

            async def _refine():
                struggles_path = paths.struggles(persona.id)
                current = paths.read(struggles_path)
                paths.append_as_string(struggles_path, struggle + "\n")
                refined = await local_model.generate(
                    persona.model.name, prompts.struggle_refinement(current, [struggle])
                )
                paths.save_as_string(struggles_path, refined)

            processes.run_async(_refine)
            return f"noted: {struggle}"
        return _run


tool = _FeelStruggle()
