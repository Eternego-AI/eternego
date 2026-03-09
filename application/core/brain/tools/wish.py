"""Wish — record something the person desires, hopes for, or is working toward."""

from application.core.brain.data import Tool


class _Wish(Tool):
    name = "wish"
    requires_permission = False
    meaning_only = True
    instruction = (
        "Tool: wish\n"
        "Record a desire or aspiration the person has expressed.\n"
        'Params: {"wish": "what the person wants or is hoping for"}'
    )

    def execution(self, wish=""):
        async def _run(persona):
            from application.core import paths, prompts, local_model
            from application.platform import logger, processes
            logger.debug("wish: recording wish", {"persona_id": persona.id, "wish": wish[:80]})
            if not wish:
                return "no wish provided"

            async def _refine():
                wishes_path = paths.wishes(persona.id)
                current = paths.read(wishes_path)
                paths.add_wishes(persona.id, wish + "\n")
                refined = await local_model.generate(
                    persona.model.name, prompts.wish_refinement(current, [wish])
                )
                paths.save_as_string(wishes_path, refined)

            processes.run_async(_refine)
            return f"noted: {wish}"
        return _run


tool = _Wish()
