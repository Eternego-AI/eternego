"""Persona — her readable knowledge in one shape.

What she keeps in human-readable form: the files she writes about people
and herself (memory) and the procedures she's learned (instruction).
Both are reachable from disk in one read. The web shows them however it
likes — one tab per memory entry, one tab for the catalog of meanings,
and tomorrow whatever else lands here.
"""

from dataclasses import dataclass, field

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.brain import meanings as meanings_loader
from application.core.data import Persona
from application.platform import logger


@dataclass
class KnowledgeData:
    memory: dict[str, str] = field(default_factory=dict)
    instruction: list[dict] = field(default_factory=list)


async def knowledge(persona: Persona) -> Outcome[KnowledgeData]:
    """Read everything the persona keeps in readable form.

    `memory` is a `{key: markdown_body}` map of the inner-world files —
    person, traits, struggles, wishes, notes, briefing. Empty files are
    omitted so the UI doesn't render dead tabs. `instruction` is the
    meanings catalog (built-in plus persona-written) as a flat list, each
    entry carrying its intention text and path prose.

    The shape is open — anything added here grows the web's menu without
    any further wiring.
    """
    bus.propose("Reading persona knowledge", {"persona": persona})
    try:
        pid = persona.id

        memory_sources = {
            "person": paths.person_identity(pid),
            "trait": paths.persona_trait(pid),
            "struggles": paths.struggles(pid),
            "wishes": paths.wishes(pid),
            "notes": paths.notes(pid),
        }
        memory = {}
        for key, path in memory_sources.items():
            body = paths.read(path)
            if body:
                memory[key] = body

        instruction = []
        for m in meanings_loader.builtin(persona).values():
            instruction.append({"intention": m.intention(), "body": m.path(), "source": "builtin"})
        for m in meanings_loader.custom(persona).values():
            instruction.append({"intention": m.intention(), "body": m.path(), "source": "custom"})

        bus.broadcast("Persona knowledge read", {"persona": persona, "memory": memory, "instruction": instruction})
        return Outcome(
            success=True,
            message="",
            data=KnowledgeData(memory=memory, instruction=instruction),
        )
    except Exception as e:
        logger.warning("Could not read persona knowledge", {"persona": persona, "error": str(e)})
        bus.broadcast("Persona knowledge read failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not read knowledge.")
