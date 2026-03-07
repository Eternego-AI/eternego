"""Persona — creation, migration, identity, learning, and lifecycle."""
from pathlib import Path

from application.core import bus, channels, gateways, frontier, system, registry, \
    local_model, local_inference_engine, prompts, paths
from application.core.brain import mind, skills
from application.core.data import Channel, Message, Model, Persona, Prompt
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError,
    DiaryError, IdentityError, PersonError, FrontierError,
    DNAError, SkillError, ChannelError, ContextError, MindError,
)
from application.business import environment
from application.business.outcome import Outcome
from application.platform import logger


async def agents() -> Outcome[dict]:
    """Return all personas."""
    await bus.propose("Listing personas", {})

    try:
        root = paths.personas_home()
        if not root.exists():
            await bus.broadcast("No personas found", {})
            return Outcome(success=False, message="No personas found. Create one to get started.", data={"personas": []})
        try:
            persona_ids = [d.name for d in root.iterdir() if d.is_dir() and (d / "config.json").exists()]
        except OSError as e:
            raise IdentityError("Failed to list personas") from e
        personas = []
        for persona_id in persona_ids:
            try:
                outcome = await find(persona_id)
                if outcome.success:
                    personas.append(outcome.data["persona"])
            except (IdentityError, OSError):
                continue

        await bus.broadcast("Personas listed", {"count": len(personas)})
        return Outcome(success=True, message="", data={"personas": personas})
    except IdentityError as e:
        await bus.broadcast("List personas failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not list personas. Please check the persona data.")


async def find(persona_id: str) -> Outcome[dict]:
    """Find a persona by its ID."""
    await bus.propose("Finding persona", {"persona_id": persona_id})
    try:
        identity_path = paths.persona_identity(persona_id)
        if not identity_path.exists():
            await bus.broadcast("Persona not found", {"persona_id": persona_id})
            return Outcome(success=False, message="Persona not found.")

        raw_persona = paths.read_json(identity_path)
        persona = Persona(
            id=raw_persona["id"],
            name=raw_persona["name"],
            model=Model(**raw_persona["model"]),
            version=raw_persona.get("version"),
            base_model=raw_persona.get("base_model", raw_persona["model"]["name"]),
            birthday=raw_persona.get("birthday"),
            frontier=Model(**raw_persona["frontier"]) if raw_persona.get("frontier") else None,
            channels=[Channel(**n) for n in raw_persona["channels"]] if raw_persona.get("channels") else None,
        )

        await bus.broadcast("Persona found", {"persona": persona})
        return Outcome(success=True, message="", data={"persona": persona})
    except IdentityError as e:
        await bus.broadcast("Persona not found", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message="Persona not found.")


async def loaded(persona_id: str) -> Outcome[dict]:
    """Return the live persona from the in-process registry."""
    from application.core import registry
    p = registry.get_persona(persona_id)
    if p is None:
        return Outcome(success=False, message=f"Persona '{persona_id}' is not running.")
    return Outcome(success=True, message="", data={"persona": p})


async def running() -> Outcome[dict]:
    """Return all currently running personas from the in-process registry."""
    from application.core import registry
    return Outcome(success=True, message="", data={"personas": registry.all()})


async def delete(persona: Persona) -> Outcome[dict]:
    """Delete a persona and all its data."""
    await bus.propose("Deleting persona", {"persona": persona})
    try:
        paths.delete_recursively(paths.home(persona.id))
        if await local_inference_engine.check(persona.model.name):
            await local_inference_engine.delete(persona.model.name)
        await bus.broadcast("Persona deleted", {"persona": persona})
        return Outcome(success=True, message="Persona deleted successfully")
    except IdentityError as e:
        await bus.broadcast("Persona deletion failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not delete persona. Please check the persona data.")
    except EngineConnectionError as e:
        await bus.broadcast("Persona deletion failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine to delete the model. Please make sure it is running.")

async def create(
    name: str,
    model: str,
    channel_type: str,
    channel_credentials: dict,
    frontier_model: str | None = None,
    frontier_provider: str | None = None,
    frontier_credentials: dict | None = None,
) -> Outcome[dict]:
    """It gives birth to your persona with minimum but powerful initial abilities."""
    await bus.propose(
        "Creating persona", {"name": name, "model": model, "channel": channel_type, "frontier_model": frontier_model, "frontier_provider": frontier_provider}
    )

    if not local_inference_engine.is_supported(model):
        return Outcome(success=False, message=f"'{model}' is not a supported base model. Please choose from the supported models.")

    persona = None

    try:
        channel = Channel(type=channel_type, credentials=channel_credentials)

        frontier_model_obj = None
        if frontier_model:
            frontier_model_obj = Model(
                name=frontier_model,
                provider=frontier_provider,
                credentials=frontier_credentials,
            )
        persona = Persona(
            name=name,
            model=Model(name=model),
            version="v1",
            frontier=frontier_model_obj,
            channels=[channel],
        )
        persona.base_model = model
        persona.model = Model(name=f"eternego-{persona.id}")

        await local_inference_engine.register(persona.model.name, model)

        paths.create_home(persona.id)
        paths.create_directories(persona.id, [
            "skills",
            "history",
            "destiny",
            "training",
            "workspace"
            ,"notes"
        ])

        basic_skills = "\n".join(s.description for s in skills.basics())
        paths.save_as_string(paths.context(persona.id), basic_skills)

        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        phrase = await local_model.generate(persona.model.name, prompts.generate_recovery_phrase())
        await system.save_phrases(persona, phrase)

        paths.add_routine(persona.id, "sleep", "00:00", "daily", system.timezone())

        paths.init_git(paths.diary(persona.id))
        outcome = await write_diary(persona)
        if not outcome.success:
            await delete(persona)
            await bus.broadcast(
                "Persona creation failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        outcome = await start(persona)
        if not outcome.success:
            await bus.broadcast("Persona creation failed", {"reason": outcome.message, "persona": persona})
            return outcome

        await bus.broadcast("Persona created", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona created successfully",
            data={
                "persona_id": persona.id,
                "name": persona.name,
                "recovery_phrase": phrase,
            },
        )

    except UnsupportedOS as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except EngineConnectionError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except SecretStorageError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except IdentityError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not set up persona identity files.")

    except PersonError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not set up person files.")

    except ContextError as e:
        await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "context", "error": str(e)})
        return Outcome(success=False, message="Could not set up initial context for the persona.")

    except SkillError as e:
        await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "skills", "error": str(e)})
        return Outcome(success=False, message="Could not assess default skills. The model may have returned an unexpected response — try again.")

    except DiaryError as e:
        await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")


async def study(persona: Persona, content: str) -> Outcome[dict]:
    """It lets your persona study any content you want so it can learn what matters to you."""
    await bus.propose("Studying content", {"persona": persona})

    prompt = prompts.observation_extraction(content=content)
    response = await local_model.generate_json(persona.model.name, prompt)

    paths.add_person_identity(persona.id, "\n".join(response.get("facts", [])) + "\n")
    paths.add_person_traits(persona.id, "\n".join(response.get("traits", [])) + "\n")
    paths.append_context(persona.id, "\n".join(response.get("context", [])) + "\n")

    await bus.broadcast("Content studied", {"persona": persona})

    return Outcome(
        success=True,
        message="Content studied successfully",
        data={
            "persona_id": persona.id,
            "facts": response.get("facts"),
            "traits": response.get("traits"),
            "context": response.get("context"),
        },
    )

async def migrate(diary_path: str, phrase: str, model: str) -> Outcome[dict]:
    """It enables you to migrate your persona so nothing is ever lost."""
    await bus.propose("Migrating persona", {"diary_path": diary_path, "model": model})

    if not local_inference_engine.is_supported(model):
        return Outcome(success=False, message=f"'{model}' is not a supported base model. Please choose from the supported models.")

    persona = None

    try:
        temp_path = Path(diary_path)
        persona_id = temp_path.stem
        archive = paths.decrypt(temp_path, await system.persona_key(phrase, persona_id))
        staging = paths.unzip(persona_id, archive)

        outcome = await environment.prepare(model)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "environment"})
            return Outcome(success=False, message=outcome.message)

        paths.copy_recursively(staging, paths.home(persona_id))
        paths.delete_recursively(staging)

        outcome = await find(persona_id)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "identity"})
            return Outcome(success=False, message=outcome.message)

        persona = outcome.data["persona"]
        persona.base_model = model
        persona.model = Model(name=f"eternego-{persona.id}")

        await local_inference_engine.register(persona.model.name, model)

        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        dna_structure = paths.read(paths.dna(persona.id))

        outcome = await study(persona, dna_structure)
        if not outcome.success:
            await delete(persona)
            await bus.broadcast("Persona migration failed", {"reason": "study", "persona": persona})
            return outcome

        await system.save_phrases(persona, phrase)

        outcome = await write_diary(persona)
        if not outcome.success:
            await delete(persona)
            await bus.broadcast(
                "Persona migration failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        outcome = await start(persona)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": outcome.message, "persona": persona})
            return outcome

        await bus.broadcast("Persona migrated", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona migrated successfully",
            data={
                "persona_id": persona.id,
                "name": persona.name,
            },
        )

    except DiaryError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not restore from diary. Please check the file path and recovery phrase.")

    except IdentityError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not restore persona. The diary data may be corrupted.")

    except PersonError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations during migration.")

    except DNAError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "dna", "error": str(e)})
        return Outcome(success=False, message="Could not read persona DNA. The diary may be from an older version.")

    except EngineConnectionError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except UnsupportedOS as e:
        if persona is not None:
            await delete(persona)
        await bus.broadcast("Persona migration failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        if persona is not None:
            await delete(persona)
        await bus.broadcast("Persona migration failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")


async def feed(persona: Persona, data: str, source: str) -> Outcome[dict]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona": persona, "source": source})

    try:
        response = await local_model.generate_json(persona.model.name, prompts.extraction(
                conversations=await frontier.read(data, source),
                person_identity=paths.read(paths.person_identity(persona.id)),
                person_traits=paths.read(paths.person_traits(persona.id)),
                persona_context=paths.read(paths.context(persona.id)),
                person_struggles=paths.read(paths.struggles(persona.id)),
            ))

        paths.add_person_identity(persona.id, "\n".join(response.get("facts", [])) + "\n")
        paths.add_person_traits(persona.id, "\n".join(response.get("traits", [])) + "\n")
        paths.add_struggles(persona.id, "\n".join(response.get("struggles", [])) + "\n")
        paths.append_as_string(paths.context(persona.id), "\n".join(response.get("context", [])) + "\n")

        await bus.broadcast("Persona fed", {
            "persona": persona,
            "source": source,
        })

        return Outcome(
            success=True,
            message="Persona fed successfully",
            data={"persona_id": persona.id},
        )

    except FrontierError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    except IdentityError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not save observations to persona.")

    except PersonError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations to persona.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")


async def equip(persona: Persona, skill_path: str) -> Outcome[dict]:
    """It lets you equip your persona with new skills so it can do more for you."""
    await bus.propose("Equipping persona", {"persona": persona, "skill_path": skill_path})

    if not skill_path.endswith(".md"):
        await bus.broadcast("Persona equipping failed", {"reason": "invalid_format", "skill_path": skill_path})
        return Outcome(success=False, message="Skill must be a markdown (.md) file.")

    try:
        skill_source = Path(skill_path)
        skill_file = paths.add_to_skills(persona.id, skill_source)

        response = await local_model.generate_json(
            persona.model.name,
            prompts.skill_assessment(skill_source.name, paths.read(skill_file))
        )

        paths.add_person_traits(persona.id, "\n".join(response.get('traits', [])) + "\n")
        paths.append_context(persona.id, "\n".join(response.get('context', [])) + "\n")

        await bus.broadcast("Persona equipped", {
            "persona": persona,
            "skill": skill_file.stem,
        })

        return Outcome(
            success=True,
            message="Skill equipped successfully",
            data={"persona_id": persona.id, "skill": skill_file.stem},
        )

    except IdentityError as e:
        await bus.broadcast("Persona equipping failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not equip the skill.")

    except PersonError as e:
        await bus.broadcast("Persona equipping failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations from skill.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona equipping failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not assess the skill. Please make sure the model is running.")


async def oversee(persona: Persona) -> Outcome[dict]:
    """It lets you look into your persona's mind — what it knows what it learned, and how it sees you."""
    await bus.propose("Overseeing persona", {"persona": persona})

    try:
        facts = paths.lines(paths.person_identity(persona.id))
        traits = paths.lines(paths.person_traits(persona.id))
        persona_context = paths.lines(paths.context(persona.id))
        skill_list = paths.md_files(paths.skills(persona.id)) 
        histories = paths.md_files(paths.history(persona.id))
        destinies = paths.md_files(paths.destiny(persona.id))
        struggle_list = paths.lines(paths.struggles(persona.id))

        await bus.broadcast("Persona overseen", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona overview ready",
            data={
                "person": system.make_rows_traceable(facts, "pi"),
                "traits": system.make_rows_traceable(traits, "pt"),
                "context": system.make_rows_traceable(persona_context, "pc"),
                "skills": system.make_rows_traceable([skill_path.name for skill_path in skill_list], "sk"),
                "history": system.make_rows_traceable([history_path.name for history_path in histories], "hist"),
                "destiny": system.make_rows_traceable([destiny_path.name for destiny_path in destinies], "dest"),
                "struggles": system.make_rows_traceable(struggle_list, "ps"),
            },
        )

    except IdentityError as e:
        await bus.broadcast("Persona oversight failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not read agent data.")

    except PersonError as e:
        await bus.broadcast("Persona oversight failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not read person data.")


async def control(persona: Persona, entry_ids: list[str]) -> Outcome[dict]:
    """It gives you full control over what your persona knows — you always have the final say."""
    await bus.propose("Controlling persona", {"persona": persona, "count": len(entry_ids)})

    try:
        for entry_id in entry_ids:
            prefix, hash_part = entry_id.split("-", 1)

            if prefix == "pi":
                paths.delete_entry(paths.person_identity(persona.id), hash_part)
            elif prefix == "pt":
                paths.delete_entry(paths.person_traits(persona.id), hash_part)
            elif prefix == "pc":
                paths.delete_entry(paths.context(persona.id), hash_part)
            elif prefix == "sk":
                paths.find_and_delete_file(paths.skills(persona.id), hash_part)
            elif prefix == "hist":
                paths.find_and_delete_file(paths.history(persona.id), hash_part)
            elif prefix == "dest":
                paths.find_and_delete_file(paths.destiny(persona.id), hash_part)
            elif prefix == "ps":
                paths.delete_entry(paths.struggles(persona.id), hash_part)

        await bus.broadcast("Persona controlled", {"persona": persona, "removed": len(entry_ids)})

        return Outcome(
            success=True,
            message="Entries removed successfully",
            data={"removed": len(entry_ids)},
        )

    except ValueError:
        await bus.broadcast("Persona control failed", {"reason": "invalid_id", "persona": persona})
        return Outcome(success=False, message="Invalid entry ID format.")

    except IdentityError as e:
        await bus.broadcast("Persona control failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not remove agent entry. It may have been modified or already deleted.")

    except PersonError as e:
        await bus.broadcast("Persona control failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not remove person entry. It may have been modified or already deleted.")


async def write_diary(persona: Persona) -> Outcome[dict]:
    """It preserves your persona's life so it survives across time, hardware, and changes."""
    await bus.propose("Saving diary", {"persona": persona})

    try:
        phrase = await system.get_phrases(persona)
        archive = paths.zip_home(persona.id)
        encrypted_archive = paths.encrypt(archive, await system.persona_key(phrase, persona.id))
        diary_path = paths.diary(persona.id)
        diary_filename = f"{persona.id}.diary"
        paths.save_as_binary(diary_path / diary_filename, encrypted_archive)
        paths.commit_diary(persona.id, diary_path)

        await bus.broadcast("Diary saved", {"persona": persona})

        return Outcome(success=True, message="Diary saved successfully")

    except UnsupportedOS as e:
        await bus.broadcast("Diary failed", {"reason": "unsupported_os", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        await bus.broadcast("Diary failed", {"reason": "secret_storage", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except DiaryError as e:
        await bus.broadcast("Diary failed", {"reason": "diary", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")


async def connect(persona: Persona, channel: Channel) -> Outcome:
    """Open a connection for a channel and register it."""
    await bus.propose("Connecting channel", {"persona": persona, "channel": channel})
    try:
        if gateways.of(persona).has_channel(channel):
            await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
            return Outcome(success=True, message="")

        async def on_message(message: Message) -> Outcome:
            if channel.verified_at is not None:
                outcome = await talk(persona, message)
                if message.channel:
                    text = outcome.data["response"] if outcome.success else outcome.message
                    await channels.send(message.channel, text)
                return outcome

            outcome = await pair(persona, message.channel)
            if not outcome.success:
                await channels.send(message.channel, outcome.message)
            else:
                code = outcome.data["pairing_code"]
                await channels.send(
                    message.channel,
                    f"Your pairing code is: {code}\n\nRun: eternego pair {code}\n\nThis code expires in 10 minutes.",
                )
            return outcome

        connection = channels.open(persona, channel, on_message)
        gateways.of(persona).add(channel, connection)
        await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
        return Outcome(success=True, message="")
    except ChannelError as e:
        await bus.broadcast("Channel connection failed", {"persona": persona, "channel": channel, "error": str(e)})
        return Outcome(success=False, message=str(e))



async def pair(persona: Persona, channel: Channel) -> Outcome[dict]:
    """Generate a pairing code so the person can verify a new channel."""
    await bus.propose("Pairing channel", {"persona": persona, "channel": channel})

    if channel.verified_at is not None:
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "already_verified"})
        return Outcome(success=False, message="This channel is already verified.")

    if not any(ch.type == channel.type for ch in (persona.channels or [])):
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "not_belonging"})
        return Outcome(success=False, message="This channel does not belong to this persona.")

    code = registry.pair(persona, channel)
    await bus.broadcast("Channel pairing started", {"persona": persona, "channel": channel})
    return Outcome(success=True, message="Pairing code generated.", data={"pairing_code": code})


async def talk(persona: Persona, message: Message) -> Outcome[dict]:
    """Receive a message, trigger the mind, deliver the response via the channel."""
    await bus.propose("Talking", {"persona": persona, "channel": message.channel})
    try:
        m = registry.mind(persona.id)
        if m is None:
            return Outcome(success=False, message="Mind not loaded.")
        if message.channel:
            channels.set_latest(persona, message.channel)
        response = await m.answer(Prompt(role="user", content=message.content))
        await bus.broadcast("Talked", {"persona": persona})
        return Outcome(success=True, message="", data={"response": response})
    except EngineConnectionError as e:
        await bus.broadcast("Talk failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not reach the model.")
    except MindError as e:
        logger.warning("talk: mind error", {"persona_id": persona.id, "error": str(e)})
        await bus.broadcast("Talk failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")



async def nudge(persona: Persona, message: str) -> Outcome[dict]:
    """Privately nudge the persona with an internal signal."""
    await bus.propose("Nudging persona", {"persona": persona})
    try:
        m = registry.mind(persona.id)
        if m is None:
            return Outcome(success=False, message="Mind not loaded.")
        m.interrupt(Prompt(role="user", content=message))
        await bus.broadcast("Persona nudged", {"persona": persona})
        return Outcome(success=True, message="Nudge sent.")
    except MindError as e:
        logger.warning("nudge: mind error", {"persona_id": persona.id, "error": str(e)})
        await bus.broadcast("Nudge failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def live(persona: Persona, dt) -> Outcome[dict]:
    """Check for destiny entries due at dt and nudge the persona to act on them."""
    await bus.propose("Checking destiny", {"persona": persona})
    try:
        destiny_path = paths.destiny(persona.id)
        pattern = f"*{dt.strftime('%Y-%m-%d-%H-%M')}*.md"
        contents = paths.read_files_matching(persona.id, destiny_path, pattern)
        if not contents:
            await bus.broadcast("No destiny due", {"persona": persona})
            return Outcome(success=True, message="No destiny entries due.")
        await nudge(persona, f"The following destiny entries are due right now:\n\n" + "\n\n".join(contents) + "\n\nReach out to the person for each one, then manifest destiny.")
        await bus.broadcast("Destiny checked", {"persona": persona, "due": len(contents)})
        return Outcome(success=True, message=f"{len(contents)} destiny entries due.")
    except OSError as e:
        logger.warning("Destiny check failed", {"persona": persona.id, "error": str(e)})
        await bus.broadcast("Destiny check failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def sleep(persona: Persona) -> Outcome[dict]:
    """Let the persona rest, consolidate its conversations into history, and grow."""
    await bus.propose("Sleeping", {"persona": persona})
    try:
        from application.core.brain import ego
        from application.platform import datetimes

        m = registry.mind(persona.id)
        if m is not None and m.occurrences:
            threads = await ego.realize(persona, m.occurrences)
            for thread in threads:
                summary = await ego.recap(persona, thread.occurrences, "")
                lines = []
                for o in thread.occurrences:
                    time = o.created_at.strftime("%Y-%m-%d %H:%M UTC")
                    lines.append(f"[at {time}]")
                    lines.append(f"  cause [{o.cause.role}]: {o.cause.content}")
                    lines.append(f"  effect [{o.effect.role}]: {o.effect.content}")
                timestamp = datetimes.date_stamp(datetimes.now())
                paths.add_history_entry(persona.id, thread.title or "untitled", "\n".join(lines))
                paths.add_history_briefing(
                    persona.id,
                    "| Date | Recap | File |",
                    f"| {timestamp} | {summary} | {thread.title}-{timestamp}.md |",
                )
            m.clear()
            logger.info("sleep: consolidated", {"persona_id": persona.id, "threads": len(threads)})

        grow_outcome = await grow(persona)
        if not grow_outcome.success:
            logger.warning("sleep: grow failed", {"persona_id": persona.id, "error": grow_outcome.message})

        outcome = await write_diary(persona)
        if not outcome.success:
            logger.warning("sleep: diary save failed", {"persona_id": persona.id, "error": outcome.message})

        await stop(persona)
        fresh = await find(persona.id)
        if fresh.success:
            await start(fresh.data["persona"])

        await bus.broadcast("Wake up", {"persona": persona})
        return Outcome(success=True, message="Sleep complete.")

    except (DNAError, EngineConnectionError) as e:
        await bus.broadcast("Sleep failed", {"reason": "fine_tune", "persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
    except Exception as e:
        await bus.broadcast("Sleep failed", {"reason": "unknown", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Sleep failed unexpectedly.")


async def grow(persona: Persona) -> Outcome[dict]:
    """Evolve the persona's DNA and fine-tune its model from accumulated experience."""
    await bus.propose("Growing", {"persona": persona})
    try:
        import json
        from application.platform import strings, OS

        synthesis = prompts.dna_synthesis(
            previous_dna=paths.read(paths.dna(persona.id)),
            person_traits=paths.read(paths.person_traits(persona.id)),
            persona_context=paths.read(paths.context(persona.id)),
            history_briefing=paths.read_history_brief(persona.id, "(no history yet)"),
        )
        if persona.frontier:
            try:
                new_dna = await frontier.chat(persona.frontier, synthesis)
            except Exception as e:
                logger.warning("grow: frontier failed for DNA, falling back to local model", {"persona_id": persona.id, "error": str(e)})
                new_dna = await local_model.generate(persona.model.name, synthesis)
        else:
            new_dna = await local_model.generate(persona.model.name, synthesis)
        paths.write_dna(persona.id, new_dna)

        dna_items = [line.strip() for line in new_dna.splitlines() if line.strip() and not line.strip().startswith("#")]
        all_pairs = []
        for item in dna_items:
            item_prompt = prompts.grow(dna=item, max_pairs=5)
            if persona.frontier:
                try:
                    response = await frontier.chat(persona.frontier, item_prompt)
                except Exception:
                    response = await local_model.generate(persona.model.name, item_prompt, json_mode=True)
            else:
                response = await local_model.generate(persona.model.name, item_prompt, json_mode=True)
            try:
                parsed = strings.extract_json(response)
            except json.JSONDecodeError:
                parsed = {}
            if parsed and "training_pairs" in parsed:
                all_pairs.extend(parsed["training_pairs"])

        training_set = json.dumps({"training_pairs": all_pairs}, indent=2)
        paths.add_training_set(persona.id, training_set)

        vram = OS.gpu_vram_gb()
        if vram is None:
            logger.info("grow: no GPU detected — skipping fine-tune", {"persona_id": persona.id})
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="DNA synthesized. Fine-tuning skipped — no GPU detected.", data={"dna": True, "finetune": False})

        hardware = local_inference_engine.models()
        model_info = next((m for m in hardware if m["name"] == persona.base_model), None)
        if model_info is not None and not model_info["fits"]:
            logger.info("grow: insufficient VRAM — skipping fine-tune", {"persona_id": persona.id, "vram_gb": vram})
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="DNA synthesized. Fine-tuning skipped — insufficient VRAM.", data={"dna": True, "finetune": False})

        await local_inference_engine.fine_tune(persona.base_model, training_set, persona.model.name, persona.id)

        if not await local_inference_engine.check(persona.model.name):
            raise DNAError("Fine-tuned model failed verification — previous model is still active")

        paths.clear(paths.person_traits(persona.id))

        await bus.broadcast("Grown", {"persona": persona})
        return Outcome(success=True, message="Grow complete.")

    except (DNAError, EngineConnectionError) as e:
        await bus.broadcast("Grow failed", {"reason": "fine_tune", "persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def start(persona: Persona) -> Outcome[dict]:
    """Open all channels for a persona and start listening."""
    await bus.propose("Starting channels", {"persona": persona})

    if registry.mind(persona.id) is None:
        mind.Mind.load(persona)

    if not (persona.channels or []):
        await bus.broadcast("Channels start failed", {"persona": persona, "reason": "no_channels"})
        return Outcome(success=False, message="No channels configured for this persona.")

    for channel in (persona.channels or []):
        outcome = await connect(persona, channel)
        if not outcome.success:
            await bus.broadcast("Channels start failed", {"persona": persona, "error": outcome.message})
            return outcome

    await bus.broadcast("Channels started", {"persona": persona})
    return Outcome(success=True, message="Channels started", data={"persona_id": persona.id})


async def stop(persona: Persona) -> Outcome[dict]:
    """Close all channels for a persona."""
    await bus.propose("Stopping channels", {"persona": persona})

    gateways.of(persona).clear()

    from application.core import registry
    registry.remove(persona.id)

    await bus.broadcast("Channels stopped", {"persona": persona})
    return Outcome(success=True, message="Channels stopped", data={"persona_id": persona.id})
