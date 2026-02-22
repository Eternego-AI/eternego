"""Knowledge abilities — loading and recording what is known about the person and persona."""

from application.platform import logger, processes
from application.core import paths
from application.core.data import Channel, Persona, Prompt, Thread
from application.core.brain.abilities._base import ability


@ability(
"Request person traits needed to respond. Items: [question about the person]",
["commander", "conversational"],
order=7)
async def load_trait(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Look up person facts and traits and return them as context."""
    logger.info("Ability: load_trait", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    parts = ["Facts:\n" + "\n".join(await paths.read(await paths.person_identity(persona.id))),
             "Traits:\n" + "\n".join(await paths.read(await paths.person_traits(persona.id)))]
    if not parts:
        return Prompt(role="user", content="No person data known yet.")
    return Prompt(role="user", content="\n\n".join(parts))


@ability(
"Request skill documents needed to proceed. Items: [skill name]",
["commander", "conversational"],
order=8)
async def load_skill(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Load the requested skill documents and return them as context. Checks brain skills first, then persona skills."""
    logger.info("Ability: load_skill", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.platform import filesystem
    from application.core.brain import skills as brain_skills
    parts = []
    for skill_name in items:
        brain = next((m for m in brain_skills.basics if m.name == skill_name), None)
        if brain:
            parts.append(f"## {skill_name}\n\n{brain.skill(persona)}")
            continue
        path = persona.storage_dir / "skills" / f"{skill_name}.md"
        if path.exists():
            parts.append(f"## {skill_name}\n\n{filesystem.read(path)}")
    if not parts:
        return Prompt(role="user", content="Skill not found.")
    return Prompt(role="user", content="\n\n".join(parts))


@ability(
"Record an identifying fact about the person — name, role, location, or any stable detail about who they are. Items: [fact]",
["commander", "conversational"],
order=11)
async def learn_identity(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Persist identity facts learned about the person."""
    logger.info("Ability: learn_identity", {"persona": persona.id, "thread": thread.id, "channel": channel.name})

    async def _run():
        from application.core import person
        await person.add_facts(persona, [str(item) for item in items])

    processes.run_async(_run)
    return None


@ability(
"Remember a new trait or preference of the person. Items: [trait]",
["commander", "conversational"],
order=12)
async def remember_trait(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Persist new traits and schedule background refinement of the traits file."""
    logger.info("Ability: remember_trait", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    observed = [str(item) for item in items]

    async def _run():
        from application.core import person
        await person.add_traits(persona, observed)
        await person.refine_traits(persona, observed)

    processes.run_async(_run)
    return None


@ability(
"Record a struggle or recurring obstacle the person faces. Items: [struggle]",
["commander", "conversational"],
order=13)
async def feel_struggle(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Persist new struggles and schedule background refinement of the struggles file."""
    logger.info("Ability: feel_struggle", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    observed = [str(item) for item in items]

    async def _run():
        from application.core import struggles
        await struggles.identify(persona, observed)
        await struggles.refine(persona, observed)

    processes.run_async(_run)
    return None


@ability(
"Update your own context with something you should remember. Items: [context note]",
["commander", "conversational"],
order=14)
async def update_context(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Persist new context notes and schedule background refinement of the context file."""
    logger.info("Ability: update_context", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    notes = [str(item) for item in items]

    async def _run():
        from application.core import agent
        await paths.append_context(persona.id, "\n".join(notes) + "\n")
        await agent.refine_context(persona, notes)

    processes.run_async(_run)
    return None
