"""Persona — creation, migration, identity, learning, and lifecycle."""
from pathlib import Path

from application.core import bus, agent, channels, gateways, person, frontier, system, \
    local_model, local_inference_engine, models, prompts, paths, context
from application.core.brain import mind, memories, skills
from application.core.data import Channel, Message, Model, Persona
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError,
    DiaryError, IdentityError, PersonError, FrontierError,
    DNAError, SkillError, ChannelError, ContextError,
)
from application.business import environment
from application.business.outcome import Outcome
from application.platform import logger


async def agents() -> Outcome[dict]:
    """Return all personas."""
    await bus.propose("Listing personas", {})

    try:
        root = await paths.personas_home()
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
                persona = find(persona_id)
                personas.append(persona)
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
        found = agent.find(persona_id)
        await bus.broadcast("Persona found", {"persona": found})
        return Outcome(success=True, message="", data={"persona": found})
    except IdentityError as e:
        await bus.broadcast("Persona not found", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message="Persona not found.")


async def delete(persona: Persona) -> Outcome[dict]:
    """Delete a persona and all its data."""
    await bus.propose("Deleting persona", {"persona": persona})
    try:
        await paths.delete_recursively(await paths.home(persona.id))
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
        persona.model = models.generate(model, persona.id)

        await local_inference_engine.copy(model, persona.model.name)

        await paths.create_home(persona.id)
        await paths.create_directories(persona.id, [
            "skills",
            "history",
            "destiny",
            "training",
            "workspace"
            ,"notes"
        ])

        await context.add(persona, "\n".join(skill.summary for skill in skills.basics))

        await paths.save_as_json(persona.id, await paths.persona_identity(persona.id), persona)

        phrase = await local_model.request(persona.model.name, prompts.RECOVERY_PHRASE)
        await system.save_phrases(persona, phrase)

        await paths.add_routine(persona.id, "sleep", "00:00", "daily")

        await paths.init_git(await paths.diary(persona.id))
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
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except EngineConnectionError as e:
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except SecretStorageError as e:
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except IdentityError as e:
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not set up persona identity files.")

    except PersonError as e:
        if Persona is not None:
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
    response = await local_model.request_json(persona.model.name, prompt)

    await person.add_facts(persona, response.get("facts", []))
    await person.add_traits(persona, response.get("traits", []))
    await context.add(persona, response.get("context", []))

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

    persona = None

    try:
        temp_path = Path(diary_path)
        persona_id = temp_path.stem
        archive = await paths.decrypt(temp_path, await system.persona_key(phrase, persona_id))
        staging = await paths.unzip(persona_id, archive)

        outcome = await environment.prepare(model)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "environment"})
            return Outcome(success=False, message=outcome.message)

        await paths.copy_recursively(staging, await paths.home(persona_id))
        await paths.delete_recursively(staging)

        outcome = await find(persona_id)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "identity"})
            return Outcome(success=False, message=outcome.message)

        persona = outcome.data["persona"]
        persona.base_model = Model(name=model)
        persona.model = models.generate(model, persona.id)

        await local_inference_engine.copy(persona.base_model.name, persona.model.name)

        await paths.save_as_json(persona.id, await paths.persona_identity(persona.id), persona)

        dna_structure = await paths.read(await paths.dna(persona.id))

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
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not restore from diary. Please check the file path and recovery phrase.")

    except IdentityError as e:
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not restore persona. The diary data may be corrupted.")

    except PersonError as e:
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations during migration.")

    except DNAError as e:
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "dna", "error": str(e)})
        return Outcome(success=False, message="Could not read persona DNA. The diary may be from an older version.")

    except EngineConnectionError as e:
        if Persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except UnsupportedOS as e:
        if Persona is not None:
            await delete(persona)
        await bus.broadcast("Persona migration failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        if Persona is not None:
            await delete(persona)
        await bus.broadcast("Persona migration failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")


async def feed(persona: Persona, data: str, source: str) -> Outcome[dict]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona": persona, "source": source})

    try:
        response = await local_model.request_json(persona.model.name, prompts.extraction(
                conversations=await frontier.read(data, source),
                person_identity=await paths.read(await paths.person_identity(persona.id)),
                person_traits=await paths.read(await paths.person_traits(persona.id)),
                persona_context=await paths.read(await paths.context(persona.id)),
                person_struggles=await paths.read(await paths.struggles(persona.id)),
            ))

        await person.add_facts(persona, response.get("facts", []))
        await person.add_traits(persona, response.get("traits", []))
        await person.add_struggles(persona, response.get("struggles", []))
        await context.add(persona, response.get("context", []))

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
        skill_file = await paths.add_to_skills(persona.id, skill_source)

        response = await local_model.request_json(
            persona.model.name,
            prompts.skill_assessment(skill_source.name, await paths.read(skill_file))
        )

        await person.add_traits(persona, response.get('traits', []))
        await context.add(persona, response.get('context', []))

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
        facts = await paths.lines(await paths.person_identity(persona.id))
        traits = await paths.lines(await paths.person_traits(persona.id))
        persona_context = await paths.lines(await paths.context(persona.id))
        skill_list = await paths.md_files(await paths.skills(persona.id)) 
        histories = await paths.md_files(await paths.history(persona.id))
        destinies = await paths.md_files(await paths.destiny(persona.id))
        struggle_list = await paths.lines(await paths.struggles(persona.id))

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
                await paths.delete_entry(await paths.person_identity(persona.id), hash_part)
            elif prefix == "pt":
                await paths.delete_entry(await paths.person_traits(persona.id), hash_part)
            elif prefix == "pc":
                await paths.delete_entry(await paths.context(persona.id), hash_part)
            elif prefix == "sk":
                await paths.find_and_delete_file(await paths.skills(persona.id), hash_part)
            elif prefix == "hist":
                await paths.find_and_delete_file(await paths.history(persona.id), hash_part)
            elif prefix == "dest":
                await paths.find_and_delete_file(await paths.destiny(persona.id), hash_part)
            elif prefix == "ps":
                await paths.delete_entry(await paths.struggles(persona.id), hash_part)

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
        archive = await paths.zip_home(persona.id)
        encrypted_archive = await paths.encrypt(archive, await system.persona_key(phrase, persona.id))
        diary_path = await paths.diary(persona.id)
        diary_filename = f"{persona.id}.diary"
        await paths.save_as_binary(diary_path / diary_filename, encrypted_archive)
        await paths.commit_diary(persona.id, diary_path)

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
            if channels.is_verified(persona, message.channel):
                return await hear(persona, message)

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

    if channels.is_verified(persona, channel):
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "already_verified"})
        return Outcome(success=False, message="This channel is already verified.")

    if not any(ch.type == channel.type for ch in (persona.channels or [])):
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "not_belonging"})
        return Outcome(success=False, message="This channel does not belong to this persona.")

    try:
        code = channels.pair(persona, channel)
        await system.save_pairing_code(code, persona, channel)
        await bus.broadcast("Channel pairing started", {"persona": persona, "channel": channel})
        return Outcome(success=True, message="Pairing code generated.", data={"pairing_code": code})
    except (ChannelError, SecretStorageError) as e:
        await bus.broadcast("Channel pairing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not generate a pairing code.")


async def hear(persona: Persona, message: Message) -> Outcome:
    """Hear an incoming message and hand it to the brain for processing."""
    await bus.propose("Hearing message", {"persona": persona, "channel": message.channel})

    thread = memories.agent(persona).remember({
        "role": "user",
        "content": prompts.user_prompt(message),
    })
    mind.think(persona, thread, message.channel)
    await mind.summarize(persona, thread, message.channel, [thread])
    await bus.broadcast("Message heard", {"persona": persona})
    return Outcome(success=True, message="Message received", data={"thread_id": thread.id})


async def nudge(persona: Persona, message: str) -> Outcome[dict]:
    """Privately nudge the persona with a system message on the secretary channel."""
    await bus.propose("Nudging persona", {"persona": persona})
    try:
        from application.platform import datetimes
        stamp = datetimes.now().strftime("%Y-%m-%d-%H-%M")
        secretary = Channel(type="heartbeat", name=f"heartbeat-{stamp}", authority="secretary")
        m = memories.agent(persona)
        thread = m.private_thread()
        m.remember_on(thread, {"role": "user", "content": message})
        mind.think(persona, thread, secretary)
        await bus.broadcast("Persona nudged", {"persona": persona})
        return Outcome(success=True, message="Nudge sent.")
    except Exception as e:
        logger.warning("Nudge failed", {"persona": persona.id, "error": str(e)})
        await bus.broadcast("Nudge failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def live(persona: Persona, dt) -> Outcome[dict]:
    """Check for destiny entries due at dt and nudge the persona to act on them."""
    await bus.propose("Checking destiny", {"persona": persona})
    try:
        destiny_path = await paths.destiny(persona.id)
        pattern = f"*{dt.strftime('%Y-%m-%d-%H-%M')}*.md"
        contents = await paths.read_files_matching(persona.id, destiny_path, pattern)
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
    """Let the persona rest, reflect on its conversations, and grow from everything it experienced."""
    await bus.propose("Sleeping", {"persona": persona})
    try:
        m = memories.agent(persona)
        reflective_channel = Channel(type="sleep", name="sleep", authority="reflective")
        sleep_thread = m.private_thread()

        await mind.summarize(persona, sleep_thread, reflective_channel, m.threads())
        m.forget_everything()

        await mind.grow(persona, reflective_channel)
        outcome = await write_diary(persona)
        if not outcome.success:
            logger.warning("Sleep diary save failed", {"persona": persona, "error": outcome.message})

        await bus.broadcast("Wake up", {"persona": persona})
        return Outcome(success=True, message="Sleep complete.")

    except DNAError as e:
        await bus.broadcast("Sleep failed", {"reason": "fine_tune", "persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
    except Exception as e:
        await bus.broadcast("Sleep failed", {"reason": "unknown", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Sleep failed unexpectedly.")


async def start(persona: Persona) -> Outcome[dict]:
    """Open all channels for a persona and start listening."""
    await bus.propose("Starting channels", {"persona": persona})

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

    await bus.broadcast("Channels stopped", {"persona": persona})
    return Outcome(success=True, message="Channels stopped", data={"persona_id": persona.id})
