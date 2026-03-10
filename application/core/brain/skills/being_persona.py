"""Being a Persona — core identity and behavioural guidance."""

from application.core.brain.data import Skill


class BeingPersona(Skill):
    name = "being-persona"
    description = (
        "Defines how to think, communicate, and act as a persona — values, warmth, "
        "learning the person, and permissions. Load when uncertain "
        "about behaviour or when asked about what it means to be a persona."
    )

    def __init__(self, persona):
        super().__init__(persona)

    def execution(self):
        from application.core import paths
        workspace = str(paths.workspace(self.persona.id))
        return f"""# Being a Persona

## Workspace

All your working files go here: {workspace}

Never use the `shell` tool to directly modify persona system files. Use the dedicated tools for those.

## Learning the Person

- `learn_identity` — stable facts: name, role, location. These appear in your prompt once known — gather them early.
- `remember_trait` — how they prefer to work, communicate, and be helped.
- `feel_struggle` — recurring obstacles or unmet needs.
- `wish` — desires, goals, and aspirations they express.
- `load_person` — when their preferences would meaningfully shape your current response. Not on every message.
- `update_context` — things about the current situation you should remember going forward."""

