"""Persona — creation, migration, identity, learning, and lifecycle."""

from application.core import bus, agent, brain, channels, gateways, memories, person, frontier, diary, system, external_llms, local_model, local_inference_engine, models, prompts, dna, skills, workspace, history, destiny, observations, struggles
from application.core.data import Channel, Message, Model, Persona
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError,
    DiaryError, IdentityError, PersonError, ExternalDataError, FrontierError,
    DNAError, SkillError, ChannelError,
)
from application.business import environment
from application.business.outcome import Outcome


async def agents() -> Outcome[dict]:
    """Return all personas."""
    await bus.propose("Listing personas", {})

    try:
        personas = await agent.personas()
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

    try:
        channel = Channel(type=channel_type, credentials=channel_credentials)

        local_model_obj = Model(name=model)
        frontier_model_obj = None
        if frontier_model:
            frontier_model_obj = Model(
                name=frontier_model,
                provider=frontier_provider,
                credentials=frontier_credentials,
            )

        persona = await agent.initialize(name, local_model_obj, frontier_model_obj, channels=[channel])

        persona_model = models.generate_name(model, persona.id)
        await agent.embody(persona, local_model_obj, persona_model)
        await local_inference_engine.copy(model, persona_model)

        try:
            await agent.build(persona)
            await dna.make(persona)
            await struggles.be_mindful(persona)
            await workspace.create(persona)
            await skills.equip(persona)
            await person.bond(persona)
            await agent.save_persona(persona)

            phrase = await system.generate_encryption_phrase(persona)

            await system.save_phrases(persona, phrase)

            await diary.open_for(persona)

            outcome = await write_diary(persona)
            if not outcome.success:
                await bus.broadcast(
                    "Persona creation failed", {"reason": "diary", "persona": persona}
                )
                await agent.remove(persona)
                await local_inference_engine.delete(persona_model)
                return Outcome(success=False, message=outcome.message)

        except Exception:
            await agent.remove(persona)
            await local_inference_engine.delete(persona_model)
            raise

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
        await bus.broadcast("Persona creation failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona creation failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except SecretStorageError as e:
        await bus.broadcast("Persona creation failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except IdentityError as e:
        await bus.broadcast("Persona creation failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not set up persona identity files.")

    except PersonError as e:
        await bus.broadcast("Persona creation failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not set up person files.")

    except SkillError as e:
        await bus.broadcast("Persona creation failed", {"reason": "skills", "error": str(e)})
        return Outcome(success=False, message="Could not assess default skills. The model may have returned an unexpected response — try again.")

    except DiaryError as e:
        await bus.broadcast("Persona creation failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")


async def migrate(diary_path: str, phrase: str, model: str) -> Outcome[dict]:
    """It enables you to migrate your persona so nothing is ever lost."""
    await bus.propose("Migrating persona", {"diary_path": diary_path, "model": model})

    try:
        materials = await diary.open(diary_path, phrase)

        outcome = await environment.prepare(model)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "environment"})
            return Outcome(success=False, message=outcome.message)

        persona = await agent.distill(materials)

        model_obj = Model(name=model)
        persona_model = models.generate_name(model, persona.id)
        await agent.embody(persona, model_obj, persona_model)
        await local_inference_engine.copy(model, persona_model)

        try:
            await agent.save_persona(persona)

            dna_structure = dna.read(persona)
            observed = await local_model.study(persona.model.name, dna_structure)
            await observations.effect(persona, observed)

            await system.save_phrases(persona, phrase)

            await diary.open_for(persona)

            outcome = await write_diary(persona)
            if not outcome.success:
                await bus.broadcast(
                    "Persona migration failed", {"reason": "diary", "persona": persona}
                )
                await agent.remove(persona)
                await local_inference_engine.delete(persona_model)
                return Outcome(success=False, message=outcome.message)

        except Exception:
            await agent.remove(persona)
            await local_inference_engine.delete(persona_model)
            raise

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
        await bus.broadcast("Persona migration failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not restore from diary. Please check the file path and recovery phrase.")

    except IdentityError as e:
        await bus.broadcast("Persona migration failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not restore persona. The diary data may be corrupted.")

    except PersonError as e:
        await bus.broadcast("Persona migration failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations during migration.")

    except DNAError as e:
        await bus.broadcast("Persona migration failed", {"reason": "dna", "error": str(e)})
        return Outcome(success=False, message="Could not read persona DNA. The diary may be from an older version.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona migration failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except UnsupportedOS as e:
        await bus.broadcast("Persona migration failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        await bus.broadcast("Persona migration failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")


async def feed(persona: Persona, data: str, source: str) -> Outcome[dict]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona": persona, "source": source})

    try:
        conversations = await external_llms.read(data, source)

        knowledge = await agent.knowledge(persona)
        observation = await local_model.observe(persona.model.name, conversations, **knowledge)
        await observations.effect(persona, observation)

        await bus.broadcast("Persona fed", {
            "persona": persona,
            "source": source,
        })

        return Outcome(
            success=True,
            message="Persona fed successfully",
            data={"persona_id": persona.id},
        )

    except ExternalDataError as e:
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
        skill_file = await skills.shelve(persona, skill_path)

        observed = await skills.summarize(persona, skill_file)
        await observations.effect(persona, observed)

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
        facts = await person.identified_by(persona)
        traits = await person.traits_toward(persona)
        agent_data = await agent.identity(persona)
        skill_list = await skills.names(persona)
        histories = await history.entries(persona)
        destinies = await destiny.entries(persona)
        struggle_list = await struggles.as_list(persona)

        await bus.broadcast("Persona overseen", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona overview ready",
            data={
                "person": system.make_rows_traceable(facts, "pi"),
                "traits": system.make_rows_traceable(traits, "pt"),
                "agent": system.make_rows_traceable(agent_data["identity"], "pai")
                    + system.make_rows_traceable(agent_data["context"], "pc"),
                "skills": system.make_rows_traceable(skill_list, "sk"),
                "history": system.make_rows_traceable(histories, "hist"),
                "destiny": system.make_rows_traceable(destinies, "dest"),
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
                await person.delete_identity(persona, hash_part)
            elif prefix == "pt":
                await person.delete_trait(persona, hash_part)
            elif prefix == "pai":
                await agent.delete_identity(persona, hash_part)
            elif prefix == "pc":
                await agent.delete_context(persona, hash_part)
            elif prefix == "sk":
                await skills.delete(persona, hash_part)
            elif prefix == "hist":
                await history.delete(persona, hash_part)
            elif prefix == "dest":
                await destiny.delete(persona, hash_part)
            elif prefix == "ps":
                await struggles.delete(persona, hash_part)

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
        await diary.record(persona.storage_dir, phrase)

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


async def sleep(persona: Persona) -> Outcome[dict]:
    """It lets your persona rest, reflect, and grow stronger from everything it experienced."""
    await bus.propose("Sleeping", {"persona": persona})

    try:
        await history.summarize_conversation(persona, memories.agent(persona).current_thread())
        memories.agent(persona).forget_everything()

        latest_knowledge = await agent.knowledge(persona)
        synthesis = prompts.dna_synthesis(
            previous_dna=dna.read(persona),
            person_traits=latest_knowledge.get("person_traits", ""),
            persona_context=latest_knowledge.get("persona_context", ""),
        )
        if persona.frontier:
            new_dna = await frontier.respond(persona.frontier, synthesis)
        else:
            new_dna = await local_model.respond(persona.model.name, [{"role": "user", "content": synthesis}])
        await dna.evolve(persona, new_dna)

        prompt = await agent.sleep(persona)

        if persona.frontier:
            training_set = await frontier.respond(persona.frontier, prompt)
        else:
            training_set = await local_model.respond(persona.model.name, [{"role": "user", "content": prompt}])

        await agent.save_training_set(persona, training_set)

        old_model = persona.model.name
        new_model = models.generate_name(persona.base_model, persona.id)
        await local_inference_engine.fine_tune(persona.base_model, training_set, new_model)

        if not await local_inference_engine.check(new_model):
            await bus.broadcast("Sleep failed", {"reason": "fine_tune", "persona": persona})
            return Outcome(success=False, message="Fine-tuned model failed verification. Previous model is still available.")

        await local_inference_engine.delete(old_model)

        await agent.wake_up(persona, new_model)

        outcome = await write_diary(persona)
        if not outcome.success:
            await bus.broadcast("Sleep failed", {"reason": "diary", "persona": persona})
            return outcome

        await bus.broadcast("Slept", {
            "persona": persona,
            "model": new_model,
            "channels": [ch for ch in (persona.channels or [])],
        })

        return Outcome(
            success=True,
            message="Persona slept and grew stronger",
            data={"persona_id": persona.id, "model": new_model},
        )

    except IdentityError as e:
        await bus.broadcast("Sleep failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not process persona files during sleep.")

    except PersonError as e:
        await bus.broadcast("Sleep failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations during sleep.")

    except EngineConnectionError as e:
        await bus.broadcast("Sleep failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the inference engine. Please make sure it is running.")

    except FrontierError as e:
        await bus.broadcast("Sleep failed", {"reason": "frontier", "error": str(e)})
        return Outcome(success=False, message="Could not reach the frontier model. Please check your credentials and connection.")


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
    brain.reason(persona, thread, message.channel)
    await bus.broadcast("Message heard", {"persona": persona})
    return Outcome(success=True, message="Message received", data={"thread_id": thread.id})


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
