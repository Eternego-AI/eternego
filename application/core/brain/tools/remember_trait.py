"""Remember trait — record a new trait or preference of the person."""

from application.core.brain.data import Tool


class _RememberTrait(Tool):
    name = "remember_trait"
    requires_permission = False
    description = (
        "Records a new trait, preference, or behavioural pattern of the person. "
        "Use when you observe something consistent about how the person thinks, works, or communicates."
    )
    instruction = (
        "Tool: remember_trait\n"
        "Record a new trait or preference observed in the person.\n"
        'Params: {"trait": "the trait to record"}'
    )

    def execution(self, trait=""):
        async def _run(persona):
            from application.core import paths, prompts, local_model
            from application.platform import logger, processes
            logger.debug("remember_trait: recording trait", {"persona_id": persona.id, "trait": trait[:80]})
            if not trait:
                return "no trait provided"

            async def _refine():
                trait_path = paths.person_traits(persona.id)
                current = paths.read(trait_path)
                paths.append_as_string(trait_path, trait + "\n")
                refined = await local_model.generate(
                    persona.model.name, prompts.trait_refinement(current, [trait])
                )
                paths.save_as_string(trait_path, refined)

            processes.run_async(_refine)
            return f"noted: {trait}"
        return _run


tool = _RememberTrait()
