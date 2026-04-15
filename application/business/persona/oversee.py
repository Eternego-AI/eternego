"""Persona — looking into what a persona knows and learned."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths, system
from application.core.data import Persona
from application.core.exceptions import IdentityError, PersonError


@dataclass
class OverseeData:
    person: list
    traits: list
    struggles: list
    wishes: list
    context: list
    history: list
    destiny: list


async def oversee(persona: Persona) -> Outcome[OverseeData]:
    """It lets you look into your persona's mind — what it knows what it learned, and how it sees you."""
    await bus.propose("Overseeing persona", {"persona": persona})

    try:
        facts = paths.lines(paths.person_identity(persona.id))
        traits = paths.lines(paths.person_traits(persona.id))
        wish_list = paths.lines(paths.wishes(persona.id))
        struggle_list = paths.lines(paths.struggles(persona.id))
        persona_context = paths.lines(paths.persona_trait(persona.id))
        histories = paths.md_files(paths.history(persona.id))
        destinies = paths.md_files(paths.destiny(persona.id))

        await bus.broadcast("Persona overseen", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona overview ready",
            data=OverseeData(
                person=system.make_rows_traceable(facts, "pi"),
                traits=system.make_rows_traceable(traits, "pt"),
                struggles=system.make_rows_traceable(struggle_list, "ps"),
                wishes=system.make_rows_traceable(wish_list, "wi"),
                context=system.make_rows_traceable(persona_context, "pc"),
                history=system.make_rows_traceable([history_path.name for history_path in histories], "hist"),
                destiny=system.make_rows_traceable([destiny_path.name for destiny_path in destinies], "dest"),
            ),
        )

    except IdentityError as e:
        await bus.broadcast("Persona oversight failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not read agent data.")

    except PersonError as e:
        await bus.broadcast("Persona oversight failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not read person data.")
