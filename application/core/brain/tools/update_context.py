"""Update context — update the persona's own context with something to remember."""

from application.core.brain.data import Tool


class _UpdateContext(Tool):
    name = "update_context"
    requires_permission = False
    description = (
        "Updates the persona's own context with a note to remember going forward. "
        "Use when something important about the current situation, relationship, or ongoing task "
        "should be retained across conversations."
    )
    instruction = (
        "Tool: update_context\n"
        "Update your own context with something you should remember.\n"
        'Params: {"note": "the context note to record"}'
    )

    def execution(self, note=""):
        async def _run(persona):
            from application.core import paths, prompts, local_model
            from application.platform import logger, processes
            logger.debug("update_context: recording context note", {"persona_id": persona.id, "note": note[:80]})
            if not note:
                return "no note provided"

            async def _refine():
                context_path = paths.context(persona.id)
                current = paths.read(context_path)
                paths.append_as_string(context_path, note + "\n")
                refined = await local_model.generate(
                    persona.model.name, prompts.context_refinement(current, [note])
                )
                paths.save_as_string(context_path, refined)

            processes.run_async(_refine)
            return f"noted: {note}"
        return _run


tool = _UpdateContext()
